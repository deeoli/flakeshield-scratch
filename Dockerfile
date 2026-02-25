FROM python:3.11-slim

# Work in /app so that everything is contained
WORKDIR /app

# Copy the repository into the container
COPY . /app

# Ensure entrypoint script is executable
RUN chmod +x entrypoint.sh

# Install the package and dependencies
RUN pip install --no-cache-dir .

# Default entrypoint forwards to the flakeshield CLI
ENTRYPOINT ["flakeshield"]
