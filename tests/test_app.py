from app import create_app, make_celery

APP = create_app('config')
celery = make_celery(APP)
from app.tasks.detect import detect_celery_task
from app.tasks.diagnose import diagnose_celery_task
from app.tasks.train import train_celery_task

celery.tasks.register(detect_celery_task)
celery.tasks.register(diagnose_celery_task)
celery.tasks.register(train_celery_task)
