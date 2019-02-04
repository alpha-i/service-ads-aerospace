web: python application.py
worker: PYTHONOPTIMIZE=1 celery -A celery_worker.celery worker -E --loglevel=debug --concurrency=1 --max-tasks-per-child=1
