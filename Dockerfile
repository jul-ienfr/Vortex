FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy source
COPY src/ src/
COPY integrations/ integrations/

# Expose port for dashboard/API
EXPOSE 8080

# Default command
CMD ["vortex", "--help"]
