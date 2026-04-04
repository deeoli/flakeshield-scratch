FROM python:3.11-slim

# Work in /app so that everything is contained
WORKDIR /app

# Copy the repository into the container
COPY . /app

# Ensure entrypoint script is executable
RUN chmod +x entrypoint.sh

# Install the package and dependencies
ARG INSTALL_SEMANTIC=false
RUN if [ "$INSTALL_SEMANTIC" = "true" ]; then \
        pip install --no-cache-dir ".[semantic]"; \
    else \
        pip install --no-cache-dir .; \
    fi

# Default entrypoint uses our helper script that maps inputs to flags
ENTRYPOINT ["sh", "/app/entrypoint.sh"]
