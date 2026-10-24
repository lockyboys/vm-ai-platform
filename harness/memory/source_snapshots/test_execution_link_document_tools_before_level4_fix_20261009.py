"""Exact Execution Link repair: no network, no identifier allocation."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from harness.mcp.tools import execution_link_document_tools as tool

FIELDS = ("mongodb_database_id","mongodb_collection_id","mongodb_document_master_id")
class Repository:
    database_name = "repo"
    def __init__(self, row):
        self.row = row
        self.calls = []
    def begin(self): self.calls.append("begin")
    def rollback(self): self.calls.append("rollback")
    def fetch_all(self, sql, params):
        self.calls.append((sql, params))
        return [] if self.row is None else [self.row]
class Mongo:
    database_name = "mongo"
    def __init__(self, document):
        self.document = document
        self.updates = []
        self.race = False
    def get_mongodb_database(self): return SimpleNamespace(name='mongo')
    def find_one(self, collection, selector):
        return deepcopy(self.document)
    def update_one(self, collection, selector, update):
        self.updates.append((collection,selector,update))
        if self.race:
            return SimpleNamespace(matched_count=0,modified_count=0)
        self.document.update(update["$set"])
        return SimpleNamespace(matched_count=1,modified_count=1)
def row():
    return {"object_attempt_id":"H1","generated_identifier":"D1",
            "object_name":"MongoDB.agent_long_term_memory",
            "mongodb_database_id":"DB1","mongodb_collection_id":"C1",
            "mongodb_document_master_id":"M1"}
def invoke(r=None, d=None, apply=False):
    r = Repository(row()) if r is None else r
    d = Mongo({"_id":"D1","payload":{"text":"keep"},"audit":{"created_by":"old"}}) if d is None else d
    return tool._repair_document(r,d,collection_name="agent_long_term_memory",
        object_attempt_id="H1",document_id="D1",apply=apply),r,d
def test_dry_run_never_updates():
    result, r, m = invoke()
    assert result["applied"] is False and len(result["updated_field_names"]) == 3
    assert m.updates == [] and r.calls[0] != "begin"
def test_apply_preserves_all_content_and_exact_link_values():
    result, r, m = invoke(apply=True)
    assert result["verified"] is True and result["modified_count"] == 1
    assert {k:m.document[k] for k in FIELDS} == {k:row()[k] for k in FIELDS}
    assert m.document["payload"] == {"text":"keep"} and m.document["audit"] == {"created_by":"old"}
    assert r.calls[0] == "begin" and r.calls[-1] == "rollback"
    assert "FOR UPDATE" in r.calls[1][0]
def test_already_correct_is_noop():
    document = {"_id":"D1",**{k:row()[k] for k in FIELDS}}
    result,_,m = invoke(d=Mongo(document),apply=True)
    assert result["updated_field_names"] == [] and not m.updates
def test_existing_id_conflict_is_not_overwritten():
    m=Mongo({"_id":"D1","mongodb_collection_id":"OTHER"})
    with pytest.raises(ValueError,match="conflict"):
        invoke(d=m,apply=True)
    assert not m.updates
@pytest.mark.parametrize("change",[
    {"generated_identifier":"wrong"},
    {"object_name":"MongoDB.other"},
    {"mongodb_document_master_id":None},
])
def test_link_mismatch_fails_closed(change):
    value=row();value.update(change);m=Mongo({"_id":"D1"})
    with pytest.raises(ValueError):
        invoke(r=Repository(value),d=m,apply=True)
    assert not m.updates
def test_missing_link_fails_closed():
    with pytest.raises(LookupError):
        invoke(r=Repository(None),apply=True)
def test_missing_document_fails_closed():
    with pytest.raises(LookupError):
        invoke(d=Mongo(None),apply=True)
def test_race_does_not_claim_success():
    m=Mongo({"_id":"D1"});m.race=True
    with pytest.raises(RuntimeError,match="changed"):
        invoke(d=m,apply=True)
def test_selector_only_exact_id_and_optimistic_field_guards():
    _,_,m=invoke(apply=True)
    selector=m.updates[0][1]
    assert selector["_id"] == "D1" and len(selector["$and"]) == 3
@pytest.mark.parametrize("raw",['{}','[]','123','null'])
def test_non_scalar_or_non_string_document_id_rejected(raw):
    with pytest.raises(ValueError):
        tool._document_identifier(raw)
def test_extended_json_object_id_is_explicit():
    assert str(tool._document_identifier('{"$oid":"0123456789abcdef01234567"}')) == "0123456789abcdef01234567"

# Verify fail-closed public routing without opening any database connection.
@pytest.mark.parametrize("collection,role", [("other","STORY"),("agent_long_term_memory","HEALTH")])
def test_public_target_rejected_before_connections(monkeypatch, collection, role):
    class NoConnections:
        _normalize_database_role = staticmethod(lambda value: value.upper())
        def __init__(self, **kwargs):
            raise AssertionError("Invalid target must not connect.")
    monkeypatch.setattr(tool, "CommonDatabase", NoConnections)
    with pytest.raises(ValueError):
        tool.mongodb_repair_execution_link_ids(role, collection, "H1", '"D1"')

def test_link_query_requires_same_object_and_mongodb_type():
    # Prevent a successful but unrelated execution from authorizing a repair.
    assert "h.object_id=l.object_id" in tool.LINK_SQL
    assert "l.execution_link_type_code='MONGODB'" in tool.LINK_SQL

def test_server_exposes_separate_repair_without_importing_oauth_runtime():
    # AST validation checks registration and syntax without starting a server.
    import ast
    from pathlib import Path
    path = Path(tool.__file__).resolve().parents[1] / "sps_harness_server.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    name = "mongodb_repair_execution_link_ids"
    assert any(isinstance(node, ast.ImportFrom) and any(alias.name == name for alias in node.names)
               for node in ast.walk(tree))
    assert any(isinstance(node, ast.Call) and isinstance(node.func, ast.Call)
               and isinstance(node.func.func, ast.Attribute) and node.func.func.attr == "tool"
               and any(isinstance(arg, ast.Name) and arg.id == name for arg in node.args)
               for node in ast.walk(tree))

def test_failed_readback_never_returns_verified_and_releases_locks():
    class FailedReadback(Mongo):
        def find_one(self, collection, selector):
            if self.updates:
                return None
            return super().find_one(collection, selector)
    repository = Repository(row())
    with pytest.raises(RuntimeError, match="read-back"):
        invoke(r=repository, d=FailedReadback({"_id":"D1"}), apply=True)
    assert repository.calls[-1] == "rollback"