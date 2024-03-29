"""empty message

Revision ID: 4df6eeb7edba
Revises: 2279b76102e0
Create Date: 2018-05-17 15:47:52.421233

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
from sqlalchemy.dialects import postgresql

revision = '4df6eeb7edba'
down_revision = '2279b76102e0'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('detection_result', 'result', type_=postgresql.JSONB)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('detection_result', 'result', type_=postgresql.JSON)
    # ### end Alembic commands ###
