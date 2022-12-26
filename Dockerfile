FROM python:3.9-slim AS builder
ADD ./autoupdate /app/autoupdate
ADD ./*.py /app
COPY requirements.txt app/requirements.txt
WORKDIR /app

# Install dependencies
RUN pip install -r requirements.txt --target=/app

# A distroless container image with Python and some basics like SSL certificates
# https://github.com/GoogleContainerTools/distroless
FROM gcr.io/distroless/python3-debian10
COPY --from=builder /app /app
WORKDIR /app
ENV PYTHONPATH /app