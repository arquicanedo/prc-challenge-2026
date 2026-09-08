FROM python:3.12-slim
WORKDIR /app
COPY main.py .
ENV PORT=8080 PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "main.py"]
