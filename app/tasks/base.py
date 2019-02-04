from celery import Task
from celery.signals import worker_process_shutdown, worker_process_init
from sqlalchemy import create_engine

from app.database import db_session
from config import SQLALCHEMY_DATABASE_URI


class BaseDBTask(Task):
    def __call__(self, *args, **kwargs):
        try:
            return super().__call__(*args, **kwargs)
        finally:
            db_session.close()


@worker_process_shutdown.connect
def on_fork_close_session(**kwargs):
    if db_session is not None:
        db_session.remove()


@worker_process_init.connect
def on_fork_open_session(**kwargs):
    engine = create_engine(SQLALCHEMY_DATABASE_URI, convert_unicode=True, pool_pre_ping=True, pool_recycle=3600)
    db_session.bind = engine
