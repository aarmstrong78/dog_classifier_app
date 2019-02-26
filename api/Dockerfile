FROM python:3.6.8-alpine3.9

COPY requirements.txt /

RUN pip install -r requirements.txt && pip install gunicorn

COPY ./. /

ENTRYPOINT ["/runserver.sh"]
