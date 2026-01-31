
FROM python:3.14-slim as builder

WORKDIR /app


RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .


RUN python -m venv /app/venv && \
    /app/venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.14-slim

WORKDIR /app


RUN apt-get update && apt-get install -y \
    supervisor \
    && rm -rf /var/lib/apt/lists/*


RUN mkdir -p /var/log/supervisor


COPY --from=builder /app/venv /app/venv


COPY . .


ENV PATH="/app/venv/bin:$PATH"
ENV PYTHONPATH="/app"


COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf


EXPOSE 8000


CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
