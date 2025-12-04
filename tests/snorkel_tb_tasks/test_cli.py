from typer.testing import CliRunner
import shutil
import yaml
from pathlib import Path
import json
import tomllib
from snorkel_tb_tasks.main import app

runner = CliRunner()


def test_tasks_create():
    """Test the tasks create command."""
    # Create .cache/terminal-bench/wizard.json with skip_terminal_bench_overview=True
    wizard_config = Path.home() / ".cache/terminal-bench/wizard.json"
    # Create the folders if they don't exist
    if not wizard_config.parent.exists():
        wizard_config.parent.mkdir(parents=True)
    with open(wizard_config, "w") as f:
        json.dump({"skip_terminal_bench_overview": True}, f)
    # Interactive commands
    input = "my-first-task\n"
    input += "Create a file called /app/hello.txt. Write 'Hello, world!' to it.\n"
    input += "END\n"
    input += "2\n"
    input += "tag1\n"
    input += "easy\n"
    input += "120\n"
    input += "60\n"
    result = runner.invoke(app, ["tasks", "create", "--no-harbor"], input=input)
    assert result.exit_code == 0, result.output
    assert "Task created successfully" in result.output

    # Check if files were created correctly
    assert Path("tasks/my-first-task/task.yaml").exists()
    assert Path("tasks/my-first-task/solution.sh").exists()
    assert Path("tasks/my-first-task/tests/test_outputs.py").exists()
    assert Path("tasks/my-first-task/.dockerignore").exists()

    # Check if task.yaml was created correctly
    with open("tasks/my-first-task/task.yaml", "r") as f:
        task_yaml = yaml.safe_load(f)
    assert task_yaml["instruction"] == "Create a file called /app/hello.txt. Write 'Hello, world!' to it."
    assert task_yaml["author_name"] == "anonymous"
    assert task_yaml["author_email"] == "anonymous"
    assert task_yaml["category"] == "build-and-dependency-management"
    assert task_yaml["tags"] == []
    assert task_yaml["difficulty"] == "unknown"
    assert task_yaml["expert_time_estimate_min"] == 120
    assert task_yaml["junior_time_estimate_min"] == 60

    # Check if Snorkel's hints were added to the task.yaml file
    with open("tasks/my-first-task/task.yaml", "r") as f:
        canary_string = "".join([line for line in f.readlines() if line.startswith("#")])
    assert "Hint from Snorkel" in canary_string

    # clean up
    shutil.rmtree("tasks/my-first-task")


def test_tasks_create_harbor():
    """Test the tasks create command."""
    # Create .cache/terminal-bench/wizard.json with skip_terminal_bench_overview=True
    wizard_config = Path.home() / ".cache/terminal-bench/wizard.json"
    # Create the folders if they don't exist
    if not wizard_config.parent.exists():
        wizard_config.parent.mkdir(parents=True)
    with open(wizard_config, "w") as f:
        json.dump({"skip_terminal_bench_overview": True}, f)
    # Interactive commands
    input = "my-first-task\n"
    input += "Create a file called /app/hello.txt. Write 'Hello, world!' to it.\n"
    input += "END\n"
    input += "2\n"
    input += "tag1\n"
    input += "easy\n"
    input += "120\n"
    input += "60\n"
    result = runner.invoke(app, ["tasks", "create"], input=input)
    assert result.exit_code == 0, result.output
    assert "Task created successfully" in result.output

    # Check if files were created correctly
    assert Path("harbor_tasks/my-first-task/task.toml").exists()
    assert Path("harbor_tasks/my-first-task/instruction.md").exists()
    assert Path("harbor_tasks/my-first-task/solution/solve.sh").exists()
    assert Path("harbor_tasks/my-first-task/tests/test.sh").exists()
    assert Path("harbor_tasks/my-first-task/tests/test_outputs.py").exists()

    # Check if task.yaml was created correctly
    with open("harbor_tasks/my-first-task/task.toml", "rb") as f:
        task_toml = tomllib.load(f)
    assert task_toml["metadata"]["author_name"] == "anonymous"
    assert task_toml["metadata"]["author_email"] == "anonymous"
    assert task_toml["metadata"]["category"] == "build-and-dependency-management"
    assert task_toml["metadata"]["tags"] == []
    assert task_toml["metadata"]["difficulty"] == "unknown"
    assert task_toml["metadata"]["expert_time_estimate_min"] == 120
    assert task_toml["metadata"]["junior_time_estimate_min"] == 60

    # clean up
    shutil.rmtree("harbor_tasks/my-first-task")