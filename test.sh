#!/usr/bin/env bash

trap "exit" INT TERM ERR
trap "kill 0" EXIT
docker-compose up -d
export APP_CONFIG=test.env
PGPASSWORD=postgres psql -h localhost -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'test'" | grep -q 1 || psql -U postgres -h localhost -c "CREATE DATABASE test"
PYTHONOPTIMIZE=1 celery -A tests.test_app.celery worker -E --loglevel=info --concurrency=1 --max-tasks-per-child=1 &
sleep 3  # give celery time to start
pytest $@ --ignore=src/ -s  -W ignore::DeprecationWarning
kill %1
docker-compose stop
wait
