import os
import pytest

from werkzeug.datastructures import FileStorage

from app.database import db_session, engine
from app.entities import CompanyEntity
from app.entities.base import EntityDeclarativeBase
from app.entities.datasource import DataSourceConfigurationEntity
from app.interpreters.datasource import FlightDatasourceInterpreter

HERE = os.path.join(os.path.dirname(__file__))

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


def test_flight_datasource_interpreter(database, company):

    datasource_configuration = DataSourceConfigurationEntity(
        company_id=company.id,
        name='StandardConfiguration',
        meta={'number_of_sensors': 8}
    )

    database.add(datasource_configuration)
    database.commit()

    test_file = os.path.join(HERE, '..', '..', 'resources', 'test_good_file_fight.hd5')
    interpreter = FlightDatasourceInterpreter()

    uploaded_file = FileStorage(open(test_file, 'rb'))

    result = interpreter.from_upload_to_dataframe(uploaded_file, datasource_configuration.id)

    assert len(result.errors) == 0, f"{result.errors} occurred. expected no errors"

    test_file = os.path.join(HERE, '..', '..', 'resources', 'test_bad_file_flight.hd5')

    uploaded_file = FileStorage(open(test_file, 'rb'))
    result = interpreter.from_upload_to_dataframe(uploaded_file, datasource_configuration.id)

    assert len(result.errors) == 2, f"No error occurred. Expected error on df orientation"
    assert 'Wrong data shape (data, sensors) (10, 40960)' in result.errors
    assert 'Wrong number of sensors 40960 found, 8 expected' in result.errors
