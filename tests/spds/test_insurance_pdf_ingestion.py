"""Regression tests for complete PDF chunk splitting and bounded embedding batches."""
from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest


PROJECT_ROOT = Path("/data/vm_project")
SOURCE_PATH = PROJECT_ROOT / "FastAPI/LangGraph/Agent_Import_RAGs/LangGraph_email_RAG_Agent.py"


def _load_pdf_helpers():
    """Load only pure ingestion helpers so tests do not initialize LLMs or databases."""
    module = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
    names = {"_chunk_text", "_create_embeddings_in_batches"}
    nodes = [node for node in module.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in nodes} == names
    isolated = ast.Module(body=nodes, type_ignores=[])
    namespace = {"os": os}
    exec(compile(isolated, str(SOURCE_PATH), "exec"), namespace)
    return namespace


def test_chunk_text_preserves_overlap_and_final_tail():
    """Every source character must appear across adjacent 1000/200 chunks."""
    chunk_text = _load_pdf_helpers()["_chunk_text"]
    original = "x" * 1901
    chunks = chunk_text(original)
    assert [len(chunk) for chunk in chunks] == [1000, 1000, 301]
    assert chunks[0] + chunks[1][200:] + chunks[2][200:] == original


def test_embedding_batches_cover_every_chunk(monkeypatch):
    """Bounded requests must still send each chunk exactly once, including the final batch."""
    helpers = _load_pdf_helpers()
    inputs = [f"chunk-{number}" for number in range(19)]
    received = []

    def fake_create_embeddings(batch):
        received.extend(batch)
        return [[float(number)] for number, _ in enumerate(batch)]

    monkeypatch.setenv("OLLAMA_EMBEDDING_BATCH_SIZE", "8")
    helpers["_create_embeddings"] = fake_create_embeddings
    embeddings = helpers["_create_embeddings_in_batches"](inputs)
    assert received == inputs
    assert len(embeddings) == len(inputs)


def test_embedding_batch_rejects_missing_embedding(monkeypatch):
    """A partial Ollama batch response must stop ingestion instead of storing incomplete rows."""
    helpers = _load_pdf_helpers()
    monkeypatch.setenv("OLLAMA_EMBEDDING_BATCH_SIZE", "4")
    helpers["_create_embeddings"] = lambda batch: [[0.0]]
    with pytest.raises(RuntimeError, match="returned 1 embeddings for 4"):
        helpers["_create_embeddings_in_batches"](["a", "b", "c", "d"])


def test_mongodb_writers_store_four_audit_fields_under_audit():
    """Both email and PDF writes must nest audit metadata in one object."""
    source = SOURCE_PATH.read_text(encoding="utf-8")
    assert source.count('"audit": {') == 2
    assert '"created_dt": datetime.now(timezone.utc)' in source
    assert '"created_by": "CODEX"' in source
    assert '"client_ip": os.getenv("CLIENT_IP", "127.0.0.1")' in source
    assert '"program_id": "SPS_MONGODB_EMAIL_RAG"' in source
    assert '"program_id": "SPS_MONGODB_DOCUMENT_PDF"' in source
