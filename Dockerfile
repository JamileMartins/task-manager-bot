FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Aplica migrações e sobe o bot (mesma sequência que era usada no Railway).
CMD ["sh", "-c", "alembic upgrade head && python -m src.main"]
