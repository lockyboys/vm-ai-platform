"""Regression tests for request-scoped model and SHAP artifact isolation."""
from pathlib import Path

from ml import trainer


def test_model_versions_are_unique_and_do_not_write_global_latest(monkeypatch, tmp_path):
    written = []

    def fake_dump(model, path):
        Path(path).write_text(str(model), encoding="utf-8")
        written.append(Path(path))

    monkeypatch.setattr(trainer, "MODEL_PATH", str(tmp_path))
    monkeypatch.setattr(trainer.joblib, "dump", fake_dump)

    first = trainer._save_model("user-a-model", "Classifier")
    second = trainer._save_model("user-b-model", "Classifier")

    assert first != second
    assert Path(first).read_text(encoding="utf-8") == "user-a-model"
    assert Path(second).read_text(encoding="utf-8") == "user-b-model"
    assert len(written) == 2
    assert not (tmp_path / "latest_model.pkl").exists()


def test_model_load_requires_the_model_path_from_this_run(monkeypatch, tmp_path):
    model_file = tmp_path / "run-model.pkl"
    model_file.write_text("model", encoding="utf-8")
    loaded = []
    sentinel = object()

    def fake_load(path):
        loaded.append(path)
        return sentinel

    monkeypatch.setattr(trainer.joblib, "load", fake_load)

    assert trainer.load_model() is None
    assert trainer.load_model(str(model_file)) is sentinel
    assert loaded == [str(model_file)]


def test_shap_artifact_paths_are_unique_and_partitioned_by_user(monkeypatch, tmp_path):
    import pipeline

    monkeypatch.setattr(pipeline, "OUTPUT_PATH", str(tmp_path))

    user_a_first = Path(pipeline._shap_output_path("user/a"))
    user_a_second = Path(pipeline._shap_output_path("user/a"))
    user_b = Path(pipeline._shap_output_path("user-b"))

    assert user_a_first != user_a_second
    assert user_a_first.parent.parent.parent != user_b.parent.parent.parent
    assert user_a_first.parts[-6] == "users"
    assert user_a_first.parts[-5] == "user_a"
