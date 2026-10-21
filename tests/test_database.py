from task_manager.config import BASE_DIR
from task_manager.database import resolve_database_url


def test_relative_sqlite_path_is_resolved_against_project_root():
    url = resolve_database_url("sqlite:///./tasks.db")

    assert url.startswith("sqlite:///")
    assert str((BASE_DIR / "tasks.db").resolve()) in url


def test_in_memory_database_is_untouched():
    assert resolve_database_url("sqlite:///:memory:") == "sqlite:///:memory:"


def test_non_sqlite_url_is_untouched():
    url = "postgresql+psycopg://user:pass@localhost:5432/tasks"

    assert resolve_database_url(url) == url
