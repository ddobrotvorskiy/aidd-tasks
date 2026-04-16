FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create uploads directory
RUN mkdir -p /uploads

RUN chmod +x entrypoint.sh

ENV FLASK_APP=app
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["./entrypoint.sh"]
