#!/bin/sh

echo "Waiting for postgres..."

while ! nc -z db 5432; do
  sleep 0.1
done

echo "PostgreSQL started"

# make directories if they are not there
mkdir -p /hpcstats/accounting
mkdir -p /hpcstats/archive
mkdir -p /hpcstats/daily_archive

# detect if the tables are existing and create if not
/usr/local/bin/python3 tacc_stats/site/manage.py makemigrations
/usr/local/bin/python3 tacc_stats/site/manage.py migrate

# then run this (gunicorn later)
/usr/local/bin/gunicorn tacc_stats.site.tacc_stats_site.wsgi --bind 0.0.0.0:8000  --env DJANGO_SETTINGS_MODULE=tacc_stats.site.tacc_stats_site.settings

