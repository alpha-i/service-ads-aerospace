from contextlib import contextmanager

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import scoped_session, sessionmaker

from config import SQLALCHEMY_DATABASE_URI

engine = create_engine(SQLALCHEMY_DATABASE_URI, convert_unicode=True, pool_pre_ping=True)
metadata = MetaData()


def get_scoped_session():
    return scoped_session(
        sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine)
    )


db_session = get_scoped_session()


@contextmanager
def local_session_scope():
    session = scoped_session(sessionmaker(bind=engine))
    yield session
    session.commit()
    session.flush()
    session.remove()


def init_db():
    metadata.create_all(bind=engine)
