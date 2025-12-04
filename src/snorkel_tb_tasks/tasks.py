from typer import Argument, Option, Typer
from terminal_bench.handlers.trial_handler import Task, TaskDifficulty
from snorkel_tb_tasks.wizard import SnorkelWizard
from pathlib import Path
from typing import Annotated

tasks_app = Typer(no_args_is_help=True)


@tasks_app.command()
def create(
    task_id: Annotated[
        str | None,
        Argument(help="Task ID (e.g. hello-world)."),
    ] = None,
    tasks_dir: Annotated[
        Path,
        Option(help="The path in which to create the new task."),
    ] = Path("tasks"),
    instruction: Annotated[
        str | None,
        Option(help="Task instruction."),
    ] = None,
    interactive: Annotated[
        bool | None,
        Option(help="Whether the solution is interactive."),
    ] = False,
    category: Annotated[
        str | None,
        Option(help="Task category."),
    ] = None,
    tags: Annotated[
        list[str] | None,
        Option(
            "--tag",
            "-t",
            help="Task tags. Can be set multiple times to add multiple tags.",
        ),
    ] = [],
    difficulty: Annotated[
        TaskDifficulty | None,
        Option(help="Task difficulty."),
    ] = TaskDifficulty.UNKNOWN,
    expert_time_estimate_min: Annotated[
        int | None,
        Option(help="Expert time estimate in minutes."),
    ] = None,
    junior_time_estimate_min: Annotated[
        int | None,
        Option(help="Junior engineer time estimate in minutes."),
    ] = None,
    harbor: Annotated[
        bool | None,
        Option(help="Whether the task is a harbor task."),
    ] = True,
):
    """Starts an interactive wizard to create a new task."""
    wizard = SnorkelWizard(
        tasks_dir=Path("tasks"),
        task_id=task_id,
        instruction=instruction,
        interactive=interactive,
        name="anonymous",
        email="anonymous",
        category=category,
        tags=tags,
        difficulty=difficulty,
        expert_time_estimate_min=expert_time_estimate_min,
        junior_time_estimate_min=junior_time_estimate_min,
    )
    wizard.run()

    # Add our hints to the task.yaml file
    task_yaml_path = Path("tasks") / wizard._task_id / "task.yaml"
    task = Task.from_yaml(task_yaml_path)
    # Get the canary string from the template-task/task.yaml file.
    # A canary string is a line (or lines) that start with # at the top of the file.
    with open(task_yaml_path, "r") as f:
        canary_string = "".join([line for line in f.readlines() if line.startswith("#")])
    # Add our own hints to the canary string.
    canary_string += "\n# Hint from Snorkel\n"
    canary_string += "# Clear and self-contained description of the task to be accomplished by the agent.\n"
    canary_string += "# The instructions will include references to the relevant resources necessary for task completion, rules and additional constraints, and a description of the success criteria.\n"
    canary_string += "# This will also contain task metadata that is not available to the agent at runtime.\n"
    task.to_yaml(task_yaml_path, canary_string=canary_string)

    if harbor:
        from harbor.cli.tasks import migrate
        import shutil

        try:
            migrate(
                input_path=Path("tasks") / wizard._task_id,
                output_path=Path("harbor_tasks"),
            )
        except Exception as e:
            print(f"Error creating task in Harbor: {e}")
        finally:
            shutil.rmtree(Path("tasks") / wizard._task_id)