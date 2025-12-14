FROM ghcr.io/laude-institute/t-bench/ubuntu-24-04:20250624

WORKDIR /app

# Install only allowed tools for the task
# Note: Base image may already have some tools installed (like perl)
# We only install what we need for the task
RUN apt-get update && apt-get install -y \
    coreutils \
    findutils \
    grep \
    sed \
    gawk \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Set locale to C for deterministic sorting (critical for manifest generation)
ENV LC_ALL=C
ENV LANG=C

# Create directory for test data
RUN mkdir -p /app/data

# Copy the test file generator script
COPY generate_test_files.sh /tmp/generate_test_files.sh

# Make it executable and run it to generate test files
RUN chmod +x /tmp/generate_test_files.sh && \
    /tmp/generate_test_files.sh && \
    rm /tmp/generate_test_files.sh

# Verify that we have at least 1000 test files
RUN FILE_COUNT=$(find /app/data -type f | wc -l) && \
    echo "Found $FILE_COUNT test files in /app/data" && \
    test $FILE_COUNT -ge 1000 || \
    (echo "ERROR: Expected at least 1000 files, found $FILE_COUNT" && exit 1)

# Create directory for test outputs
RUN mkdir -p /app/output

# Set bash as default shell
SHELL ["/bin/bash", "-c"]

# Display environment info for debugging
RUN echo "Environment setup complete:" && \
    echo "- Working directory: $(pwd)" && \
    echo "- Bash version: $(bash --version | head -n1)" && \
    echo "- Test files: $(find /app/data -type f | wc -l)" && \
    echo "- Locale: $LC_ALL"
