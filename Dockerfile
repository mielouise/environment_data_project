FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
COPY requirements-dev.txt .
COPY pyproject.toml .

RUN pip install --no-cache-dir -r requirements-dev.txt

COPY app ./app
COPY tests ./tests

CMD ["python", "-m", "app.main"]