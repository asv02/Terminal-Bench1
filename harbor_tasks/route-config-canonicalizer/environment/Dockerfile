# Hint from Snorkel
# Base Dockerfile or image that fully sets up the environment, including all required tools, resources, and dependencies.
# It should be reproducible, lightweight, and run without privileged mode.

FROM python:3.13-slim-bookworm

WORKDIR /app

# Runtime-only dependencies for the routecanon package (tests install their own deps at runtime).
RUN pip install --no-cache-dir \
    pandas==2.3.3 \
    pyarrow==22.0.0 \
    pyyaml==6.0.3
