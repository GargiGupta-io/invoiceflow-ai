FROM node:22-alpine@sha256:16e22a550f3863206a3f701448c45f7912c6896a62de43add43bb9c86130c3e2 AS reviewer-build

WORKDIR /reviewer

COPY reviewer/package.json reviewer/package-lock.json ./
RUN npm ci

COPY reviewer/ ./
RUN npm run build

FROM python:3.11-alpine3.23@sha256:f73754c398b259dfbbe482361dca8b464dea57da74efe5214966ca2ee767ee12 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000

RUN apk add --no-cache \
        libgomp \
        poppler-utils \
        tesseract-ocr \
        tesseract-ocr-data-eng

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=reviewer-build /reviewer/dist /app/reviewer/dist

RUN addgroup --gid 10001 invoiceflow \
    && adduser --uid 10001 --ingroup invoiceflow --disabled-password --no-create-home invoiceflow

USER 10001:10001

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
