#!/bin/bash

gunicorn --log-level debug --log-file=- --workers 4 --name app -b 0.0.0.0:8001 --reload app.app:app
