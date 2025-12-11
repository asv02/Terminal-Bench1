from typer import Argument, Option, Typer
from terminal_bench.handlers.trial_handler import TaskDifficulty
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