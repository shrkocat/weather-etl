FROM python:3.12-slim

WORKDIR /app

# System deps needed by psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default: run the pipeline once. Override the command to run the
# dashboard instead, e.g.:
#   docker compose run app streamlit run dashboard/app.py --server.address=0.0.0.0
CMD ["python", "-m", "src.main"]
