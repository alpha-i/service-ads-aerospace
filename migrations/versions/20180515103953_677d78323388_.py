"""empty message

Revision ID: 677d78323388
Revises: 36ec82ca4640
Create Date: 2018-05-15 10:39:53.202203

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '677d78323388'
down_revision = '36ec82ca4640'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('detection_task', sa.Column('upload_code', sa.String(length=60), nullable=False))
    op.drop_constraint('detection_task_task_code_key', 'detection_task', type_='unique')
    op.create_unique_constraint(None, 'detection_task', ['upload_code'])
    op.drop_column('detection_task', 'task_code')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('detection_task', sa.Column('task_code', sa.VARCHAR(length=60), autoincrement=False, nullable=False))
    op.drop_constraint(None, 'detection_task', type_='unique')
    op.create_unique_constraint('detection_task_task_code_key', 'detection_task', ['task_code'])
    op.drop_column('detection_task', 'upload_code')
    # ### end Alembic commands ###
