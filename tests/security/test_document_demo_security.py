"""Regression test for disabled global document-demo asset access."""

from pathlib import Path


def test_document_demo_global_asset_route_is_fail_closed() -> None:
    source = (
        Path(__file__).resolve().parents[2] / "web" / "document_demo_app.py"
    ).read_text(encoding="utf-8")

    assert "def _configured_demo_report" not in source
    assert 'def preview_demo_report():\n        """Configured global report assets are disabled' in source
    assert "work_repository.get_stored_asset" not in source


def test_document_demo_uses_a_dedicated_jwt_secret() -> None:
    source = (
        Path(__file__).resolve().parents[2] / "web" / "document_demo_app.py"
    ).read_text(encoding="utf-8")

    assert 'CommonAuth(secret_key=_required_setting("SPS_DOCUMENT_DEMO_JWT_SECRET_KEY"))' in source
    assert "auth = CommonAuth()" not in source
