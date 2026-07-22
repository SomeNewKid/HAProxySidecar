FROM python:3.12-slim

WORKDIR /opt/mcp-sidecar

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN useradd --create-home --shell /usr/sbin/nologin mcp-sidecar

RUN python -m pip install --no-cache-dir mcp

COPY src/mcp_sidecar ./mcp_sidecar

USER mcp-sidecar

EXPOSE 8000

CMD ["python", "-m", "mcp_sidecar"]
