# Use the root Dockerfile: docker build -t cloudflow-backend .
FROM cloudflow-backend:latest
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
