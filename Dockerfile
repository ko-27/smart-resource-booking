FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY tests ./tests
COPY pytest.ini .

EXPOSE 5000

CMD ["flask", "--app", "backend.app", "run", "--host=0.0.0.0", "--port=5000"]