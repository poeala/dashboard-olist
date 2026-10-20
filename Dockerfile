FROM python:3.13-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt requirements-server.txt ./
RUN pip install --no-cache-dir -r requirements-server.txt
COPY app.py config.py ./
COPY assets ./assets
COPY callbacks ./callbacks
COPY components ./components
COPY data ./data
COPY views ./views
RUN useradd --create-home dashboard
USER dashboard
EXPOSE 8050
CMD ["gunicorn", "--bind", "0.0.0.0:8050", "--workers", "2", "--timeout", "180", "--access-logfile", "-", "--error-logfile", "-", "app:server"]
