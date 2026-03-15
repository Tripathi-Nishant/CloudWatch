FROM python:3.11-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY driftwatch/ ./driftwatch/
COPY data/       ./data/
COPY setup.py    .

# Install package
RUN pip install -e .

EXPOSE 8000

ENV PYTHONPATH=/app

CMD ["uvicorn", "driftwatch.api.main:app", "--host", "0.0.0.0", "--port", "8000"]