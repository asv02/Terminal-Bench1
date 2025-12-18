# Hint from Snorkel
# Base Dockerfile or image that fully sets up the environment, including all required tools, resources, and dependencies.
# It should be reproducible, lightweight, and run without privileged mode.

FROM python:3.13-slim-bookworm

WORKDIR /app

COPY simulate_flux.py /app/simulate_flux.py

RUN python3 simulate_flux.py