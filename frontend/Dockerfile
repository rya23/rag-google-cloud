FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN chmod +x /app/entrypoint.sh

EXPOSE 8080

CMD ["/app/entrypoint.sh"]
