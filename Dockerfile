FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home harvy && mkdir -p /app/data && chown -R harvy:harvy /app
USER harvy
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["gunicorn", "--workers", "1", "--threads", "4", "--bind", "0.0.0.0:8000", "--timeout", "120", "web_app:create_app()"]
