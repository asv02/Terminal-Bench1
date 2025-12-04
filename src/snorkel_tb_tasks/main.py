from typer import Typer
from snorkel_tb_tasks.tasks import tasks_app

app = Typer(no_args_is_help=True)
app.add_typer(tasks_app, name="tasks")

if __name__ == "__main__":
    app()
