FROM python:3.13-alpine
LABEL org.opencontainers.image.source="https://github.com/CDLUC3/arksorg-site"

RUN apk add --no-cache git

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install uvicorn

COPY docker/docker-config.env .env
COPY arks/ arks/
COPY docker/entrypoint.sh .

ENTRYPOINT ["./entrypoint.sh"]
EXPOSE 8000
