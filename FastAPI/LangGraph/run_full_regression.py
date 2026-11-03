import pytest

if __name__ == "__main__":
    raise SystemExit(pytest.main(["tests", "harness/tests", "--ignore-glob=*_BACKUP_*.py", "--import-mode=importlib", "-q", "--tb=no"]))
