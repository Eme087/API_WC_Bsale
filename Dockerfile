FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt ./
COPY webhook_receiver.py ./

RUN pip install --no-cache-dir -r requirements.txt

ENV PORT=8080
EXPOSE 8080

CMD ["python", "webhook_receiver.py"]
