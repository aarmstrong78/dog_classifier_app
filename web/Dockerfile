FROM python:3.6.6

COPY ./. /


RUN pip install -r requirements.txt && pip install gunicorn

ENTRYPOINT ["/runserver.sh"]
