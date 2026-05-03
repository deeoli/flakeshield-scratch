FROM python:3.11-slim

# Work in /app so that everything is contained
WORKDIR /app

# Copy the repository into the container
COPY . /app

# Ensure entrypoint script is executable
RUN chmod +x entrypoint.sh

# Install the package and full semantic stack for the action image.
# GitHub Actions cannot pass docker build-args from action.yml `args:` (those are
# container CMD only). Workflows use enable_semantic at runtime; image must include
# sentence-transformers and its stack.
RUN pip install --no-cache-dir ".[semantic]"

# Default entrypoint uses our helper script that maps inputs to flags
ENTRYPOINT ["sh", "/app/entrypoint.sh"]
