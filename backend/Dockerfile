FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.lock.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app /app/backend/app
COPY queries /app/queries
COPY benchmarks /app/benchmarks
ENV PRIVATE_STATE_DIR=/private
ENV PYTHONPATH=/app/backend
EXPOSE 8000
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
