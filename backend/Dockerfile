FROM python:3.12-slim
WORKDIR /srv
COPY pyproject.toml ./
RUN pip install --no-cache-dir "fastapi==0.115.6" "uvicorn[standard]==0.34.0" "sqlalchemy==2.0.36" \
  "alembic==1.14.0" "pydantic==2.10.4" "pydantic-settings==2.7.0" "psycopg2-binary==2.9.10" \
  "python-jose[cryptography]==3.3.0" "bcrypt==4.2.1" "celery==5.4.0" "redis==5.2.1" \
  "httpx==0.28.1" "python-multipart==0.0.20" "email-validator==2.2.0"
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
EXPOSE 8000
HEALTHCHECK --interval=20s --timeout=4s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/v1/healthz')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
