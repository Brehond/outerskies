#!/bin/sh
set -e
 
python manage.py migrate --noinput
python manage.py collectstatic --noinput
exec gunicorn astrology_ai.wsgi:application --bind 0.0.0.0:8000 