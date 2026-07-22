FROM python:3.12-slim

WORKDIR /opt/code-sidecar

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN useradd --create-home --shell /usr/sbin/nologin code-sidecar

COPY src/code_sidecar ./code_sidecar

USER code-sidecar

EXPOSE 8090

CMD ["python", "-m", "code_sidecar"]
