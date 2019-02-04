import pytest

from app.database import db_session, engine
from app.entities import TrainingTaskEntity, DataSourceEntity, CompanyEntity, UserEntity, CompanyConfigurationEntity
from app.entities.base import EntityDeclarativeBase
from app.entities.datasource import DataSourceConfigurationEntity, UploadTypes


@pytest.fixture(scope='module')
def database():
    db_session.close()
    db_session.remove()
    EntityDeclarativeBase.metadata.create_all(engine)
    yield db_session
    db_session.close()
    db_session.remove()
    EntityDeclarativeBase.metadata.drop_all(engine)


@pytest.fixture(scope='module')
def company(database):
    company_entity = CompanyEntity(
        name='TestCompany',
        domain='alpha-i.co'
    )
    database.add(company_entity)
    database.commit()
    return company_entity


@pytest.fixture(scope='module')
def company_configuration(database, company, user):
    company_configuration = CompanyConfigurationEntity(
        company_id=company.id,
        user_id=user.id
    )
    database.add(company_configuration)
    database.commit()
    return company_configuration


@pytest.fixture(scope='module')
def user(database, company):
    user = UserEntity(
        email='gabriele@alpha-i.co',
        company_id=company.id
    )

    user.hash_password('password')
    database.add(user)
    database.commit()
    return user


def test_training_task_can_be_created(database, company, company_configuration, user):
    datasource_configuration = DataSourceConfigurationEntity(
        company_id=company.id,
        name='StandardConfiguration',
        meta={'meh': 'mah'}

    )
    database.add(datasource_configuration)
    database.commit()

    first_datasource = DataSourceEntity(
        user_id=user.id,
        company_id=company.id,
        datasource_configuration_id=datasource_configuration.id,
        name='first',
        upload_code='akjlhfkhl',
        type=UploadTypes.FILESYSTEM,
        filename='first.hdf5'
    )
    database.add(first_datasource)

    second_datasource = DataSourceEntity(
        user_id=user.id,
        company_id=company.id,
        datasource_configuration_id=datasource_configuration.id,
        name='second',
        upload_code='kjajhfklah',
        type=UploadTypes.FILESYSTEM,
        filename='second.hdf5'
    )
    database.add(second_datasource)
    database.commit()

    datasources = DataSourceEntity.get_for_datasource_configuration(datasource_configuration)

    training_task = TrainingTaskEntity(
        datasource_configuration_id=datasource_configuration.id,
        company_id=company.id,
        user_id=user.id,
        task_code='my_Task_code',
        datasources=datasources,
        company_configuration_id=company_configuration.id,
        configuration={'load_path': '/something/something'}
    )

    database.add(training_task)
    database.commit()

    assert len(training_task.datasources) == 2
    assert {datasource.name for datasource in training_task.datasources} == {'first', 'second'}
