## Files

### tests/test_outputs.py

test_outputs.py should be a python test file that uses pytest.

Inside this file, we write the tests that were defined in task.yaml.
Make sure that these tests are defined in the task!
Notice that we describe the tests in this block in task.yaml:

```
The test case is one particular popular challenge on vimgolf, and validating that the file exists, the string inside is a valid solution, and the length is at most 1.5 times the best submission on the leaderboard.
We also check that the start, end, score, and challenge files all exist.
We also check that the start and end files match the challenge in vimgolf.
```

Some common commands and use cases and explanations are provided:

`tb run --agent oracle --task-id vim-golf --dataset-path annotated_tasks`
This command will run the oracle (solution.sh) and run the test_outputs.py after the solution runs.
You must use this to make sure that your solution works.

`tb run --agent claude-code --model anthropic/claude-sonnet-4-5-20250929 -t vim-golf --n-attempts 10 --dataset-path annotated_tasks`
This command will run the claude-sonnet-4.5 model with the claude-code agent 10 times. It will run test_outputs.py at the end,
and will print how many successes happened (resolved trials) and how many fails (unresolved trials), as well as a few other
statistics.

`tb run --agent codex --model openai/gpt-5 -t vim-golf --n-attempts 10 --dataset-path annotated_tasks`
This command will run the gpt-5 model with the codex agent 10 times. It will run test_outputs.py at the end,
and will print how many successes happened (resolved trials) and how many fails (unresolved trials), as well as a few other
statistics.

Notice the `--dataset-path annotated_tasks` flag. This is because this folder is in a different folder (annotated_tasks) rather than the standard tasks folder.

### .dockerignore

This file ensures that the files related to the task tracking will not be put into the Dockerfile. You should not change this file.

### docker-compose.yaml

This file will only need to be changed if you have an additional service you want to deploy in the agent's environment. For example, if you want to deploy a minio container in the same environment, you can do that via this file. Otherwise, do not change this file.

### Dockerfile

This file sets up the agent environment. Here, we can install python packages via `RUN pip install vimgolf==0.5.2`, install OS packages via `RUN apt update && apt install -y libssl-dev`, and whatever else you want.

One additional use case is to add files into the environment. We can do that via a `COPY` command.

In this vimgolf example, we copy the `challenge.txt` file in via `COPY challenge.txt /app/challenge.txt`.

Unless absolutely necessary, you must use one of the terminal-bench images as your base image, so either:
`FROM ghcr.io/laude-institute/t-bench/ubuntu-24-04:20250624` -OR- `FROM ghcr.io/laude-institute/t-bench/python-3-13:20250620`

You SHOULD NOT copy the solution, or any of the other terminal-bench files. If you do this, this will allow the agent to look at the solution, which is not allowed.

### run-tests.sh

This file runs the test outputs after the oracle runs (solution.sh), or the agent finishes running/times out. You may need to change it if you need to use a specific python package in your test_outputs.py by adding a `uv add <package>==<package version>`. For instance, if you need to use vimgolf==0.5.2 in your test_outputs.py, you can add a `uv add vimgolf==0.5.2` to this file after `uv add pytest==8.4.1`. Apart from that, in most cases, you will not need to change this file.

### solution.sh

This file is used in the oracle solution. You can test it on your test cases via
`tb run --agent oracle --task-id vim-golf --dataset-path annotated_tasks`

This solution should be self-contained, and should not be hard-coded. It should simulate commands that the agent needs to run to achieve a solution that passes the tests in `tests/test_outputs.py`.

When testing, one thing you can do to see where the solution ends up is the following:
`tb tasks interact -t vim-golf --tasks-dir annotated_tasks`

This will run the exact docker environment that the agent and oracle will be running in. From there, you can test your solution script.

### solution.yaml

In general this approach is not preferred, and you should use solution.sh instead. However, if you must provide interactive input into the shell, you can use the solution.yaml file. For more information, please see https://www.tbench.ai/docs/task-overview#yaml-approach-supports-interactive-commands

### task.yaml

This should be a natural language description of your task. The task should be well defined and self contained. You should specify any additional files needed as input or output in the task description as well. For example, for our case, we specifically mention that we take in a challenge ID found at `/app/challenge.txt`. Also, we mention that we expect certain files, such as `/app/score.txt`, `/app/start.txt`, and `/app/end.txt` to exist, and the specification for them as well.

Furthermore, you MUST include a description of the success criteria for the task. For instance, in our case, we describe the test cases clearly:
```
The test case is one particular popular challenge on vimgolf, and validating that the file exists, the string inside is a valid solution, and the length is at most 1.5 times the best submission on the leaderboard.
We also check that the start, end, score, and challenge files all exist.
We also check that the start and end files match the challenge in vimgolf.
```

You can create a task via:
`uv run stb tasks create`
and follow the prompts.

Unique Task ID: The name of your task, which will correspond to the folder generated.
Instruction: The instructions for the agent, which will need to satisfy the specification above.
Interactive Commands: Whether the task requires interactive commands.
Category: The topic of your task.
Tags: A list of tags separated by spaces that correspond to your task.
Difficulty: The prompt describes the difficulty of the problem. Note this difficulty does not necessarily correspond to the accuracy of the LLM.
Expert Time Estimate: How long it would take an expert to solve this.
Junior Engineer Time Estimate: How long it would take a junior engineer to solve this.