# Snorkel Terminal-Bench Tasks
This is a private repository to receive Terminal-Bench (TB) task submissions.

# How to get started
## Install UV

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

or see [here](https://docs.astral.sh/uv/getting-started/installation/) for more details.

## Clone this repository

```bash
git clone git@github.com:snorkel-ai/snorkel-tb-tasks.git
cd snorkel-tb-tasks
```

## Read the annotated task readme

Read annotated_task/README.md

## Create a new task using Task Wizard

```bash
uv run stb tasks create
```

The interactive wizard will help create a folder with some boilerplate files under /tasks folder.

## Complete a task creation

See [here](https://www.tbench.ai/docs/task-quickstart).

# How to submit a task

1. Push a branch to the private repo
2. Create a pull-request
3. Make sure all CI tests pass