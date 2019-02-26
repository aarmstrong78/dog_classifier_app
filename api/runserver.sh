#!/bin/bash

gunicorn -b :$PORT app.app:app
