FROM python:3.10-slim

COPY requirements.txt requirements.txt

RUN apt-get update && apt-get -y install build-essential libpq-dev gcc curl && pip install psycopg2
RUN pip3 install -r requirements.txt
