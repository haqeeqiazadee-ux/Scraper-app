FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt pydantic-settings

# Copy application code
COPY packages/ packages/
COPY services/ services/
COPY apps/web/dist/ apps/web/dist/

# Fix symlinks (services use hyphens, Python needs underscores)
RUN cd services && \
    ln -sf control-plane control_plane && \
    ln -sf worker-ai worker_ai && \
    ln -sf worker-browser worker_browser && \
    ln -sf worker-hard-target worker_hard_target && \
    ln -sf worker-http worker_http

# Create non-root user
RUN useradd -m appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "services.control_plane.app:app", "--host", "0.0.0.0", "--port", "8000"]
