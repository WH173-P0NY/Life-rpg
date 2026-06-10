FROM node:24-bookworm-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM python:3.14-slim AS app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY manage.py ./
COPY config/ ./config/
COPY activities/ ./activities/
COPY dashboard/ ./dashboard/
COPY planner/ ./planner/
COPY rpg/ ./rpg/
COPY skills/ ./skills/
COPY statuses/ ./statuses/
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist/

RUN addgroup --system app && adduser --system --ingroup app app \
    && chown -R app:app /app

USER app

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
