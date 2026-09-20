FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir --only-binary=:all: -r requirements.txt

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .
COPY start.sh .

RUN useradd -m appuser

USER appuser

CMD ["sh", "start.sh"]