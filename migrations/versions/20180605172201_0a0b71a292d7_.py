"""empty message

Revision ID: 0a0b71a292d7
Revises: ebd1bfd7db14
Create Date: 2018-06-05 17:22:01.784755

"""
from alembic import op
from sqlalchemy.orm.session import Session

# revision identifiers, used by Alembic.
from app.entities import CompanyEntity
from app.entities.datasource import DataSourceConfigurationEntity, DataSourceEntity

revision = '0a0b71a292d7'
down_revision = 'ebd1bfd7db14'
branch_labels = None
depends_on = None

DATASOURCE_CONFIG_NAME = "8 SENSORS DATA"
DATASOURCE_META = {
    "sample_rate": 1024,
    "number_of_sensors": 8
}


def upgrade():
    session = Session(op.get_bind())

    for company in session.query(CompanyEntity).all():

        datasource_config = DataSourceConfigurationEntity(
            name=DATASOURCE_CONFIG_NAME,
            meta=DATASOURCE_META,
            company_id=company.id
        )

        session.add(datasource_config)
        for ds_entity in session.query(DataSourceEntity).filter(DataSourceEntity.company_id == company.id).all():
            ds_entity.datasource_configuration_id = datasource_config.id
            ds_entity.meta = datasource_config.meta
            session.merge(ds_entity)

    op.alter_column('data_source', 'datasource_configuration_id', nullable=False)


def downgrade():

    session = Session(op.get_bind())

    op.alter_column('data_source', 'datasource_configuration_id', nullable=True)
    for ds in session.query(DataSourceEntity).all():
        ds.datasource_configuration_id = None
        session.merge(ds)

    session.query(DataSourceConfigurationEntity).delete()
