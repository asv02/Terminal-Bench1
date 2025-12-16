FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ patchelf ccache \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Pin dependency
RUN pip install nuitka==1.8.6

# Copy only required runtime files
COPY game_engine.py /app/
COPY challenges/ /app/challenges/

# Compile validators
RUN cd /app/challenges && \
    for f in *_validator.py; do \
        python3 -m nuitka --standalone --onefile --remove-output --lto=yes "$f"; \
        rm "$f"; \
        out="${f%.*}"; \
        [ -f "$out.bin" ] && mv "$out.bin" "$out"; \
    done

# Compile engine
RUN python3 -m nuitka --standalone --onefile --remove-output --lto=yes game_engine.py && \
    mv game_engine.bin game_engine && \
    chmod +x game_engine

# Cleanup source
RUN rm game_engine.py

# Runtime dirs
RUN mkdir -p /app/solutions

# Make engine executable
RUN chmod +x /app/game_engine

WORKDIR /app

# Keep container alive for agent execution
CMD ["/bin/bash"]

