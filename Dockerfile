FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Buat direktori yang dibutuhkan
RUN mkdir -p config tmp_posegen

EXPOSE 5003

CMD ["python", "app.py"]
