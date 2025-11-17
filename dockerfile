FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY requirements.txt /app/

RUN pip install -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python","main.py"]