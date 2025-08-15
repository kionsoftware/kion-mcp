# Multi-stage build for Kion MCP Server
# Stage 1: Builder image with uv
FROM python:3.13-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock README.md LICENSE ./

# Create virtual environment and install dependencies
RUN uv sync --frozen --no-cache

# Copy source code
COPY src/ ./src/

# Install the package in the virtual environment
RUN uv pip install --no-cache-dir -e .

# Stage 2: Runtime image
FROM python:3.13-slim AS runtime

# Set working directory
WORKDIR /app

# Copy the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy source code and required spec file
COPY --from=builder /app/src /app/src
COPY fixed_spec.json /app/

# Make sure we use venv
ENV PATH="/app/.venv/bin:$PATH"

# Create non-root user for security
RUN groupadd -r mcp && useradd -r -g mcp mcp
RUN chown -R mcp:mcp /app
USER mcp

# Set the entrypoint to run the MCP server
CMD ["python", "-m", "kion_mcp.server"]
