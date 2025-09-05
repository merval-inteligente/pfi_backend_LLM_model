FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY common ./common
COPY scraper_worker.py ml_worker.py ./
COPY .env ./.env
CMD ["python", "scraper_worker.py"]
