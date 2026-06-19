FROM python:3.10-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN mkdir -p logs outputs/charts outputs/reports models data data_lake uploads
EXPOSE 8000
CMD ["python3", "run_server.py"]
