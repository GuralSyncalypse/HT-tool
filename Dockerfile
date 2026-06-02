FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    libnss3 \
    libgbm1 \
    libxss1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "worker.py"]