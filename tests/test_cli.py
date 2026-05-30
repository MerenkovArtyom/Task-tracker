from pathlib import Path

from typer.testing import CliRunner

from todo_tracker.cli import app


runner = CliRunner()


def test_cli_add_and_list_active_tasks(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'tasks.db'}"

    result = runner.invoke(
        app,
        [
            "--db-url",
            db_url,
            "add",
            "--title",
            "Buy milk",
            "--content",
            "2 bottles",
            "--priority",
            "1",
        ],
    )
    assert result.exit_code == 0

    result = runner.invoke(app, ["--db-url", db_url, "list"])

    assert result.exit_code == 0
    assert "1. [in_progress] Buy milk" in result.stdout


def test_cli_update_and_done_use_one_based_numbers(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'tasks.db'}"
    runner.invoke(
        app,
        ["--db-url", db_url, "add", "--title", "First", "--content", "A", "--priority", "1"],
    )
    runner.invoke(
        app,
        ["--db-url", db_url, "add", "--title", "Second", "--content", "B", "--priority", "2"],
    )

    update_result = runner.invoke(
        app,
        [
            "--db-url",
            db_url,
            "update",
            "1",
            "--title",
            "Updated first",
            "--content",
            "updated",
            "--priority",
            "3",
        ],
    )
    done_result = runner.invoke(app, ["--db-url", db_url, "done", "1"])
    list_result = runner.invoke(app, ["--db-url", db_url, "list"])

    assert update_result.exit_code == 0
    assert done_result.exit_code == 0
    assert "1. [in_progress] Updated first" in list_result.stdout
    assert "Second" not in list_result.stdout


def test_cli_delete_removes_all_done_tasks(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'tasks.db'}"
    runner.invoke(
        app,
        ["--db-url", db_url, "add", "--title", "Active", "--content", "A", "--priority", "1"],
    )
    runner.invoke(
        app,
        ["--db-url", db_url, "add", "--title", "Done", "--content", "B", "--priority", "2"],
    )
    runner.invoke(app, ["--db-url", db_url, "done", "2"])

    delete_result = runner.invoke(app, ["--db-url", db_url, "delete"])
    list_result = runner.invoke(app, ["--db-url", db_url, "list"])

    assert delete_result.exit_code == 0
    assert "Deleted 1 done task" in delete_result.stdout
    assert "Active" in list_result.stdout
    assert "Done" not in list_result.stdout


def test_cli_rejects_number_out_of_range(tmp_path: Path) -> None:
    db_url = f"sqlite:///{tmp_path / 'tasks.db'}"
    runner.invoke(
        app,
        ["--db-url", db_url, "add", "--title", "Only", "--content", "A", "--priority", "1"],
    )

    result = runner.invoke(app, ["--db-url", db_url, "done", "2"])

    assert result.exit_code == 1
    assert "Task number 2 was not found" in result.stdout
