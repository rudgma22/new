"""Initial migration.

Revision ID: e3423248cf2e
Revises: 
Create Date: 2024-09-14 10:17:31.648536

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e3423248cf2e'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('outing_requests', schema=None) as batch_op:
        batch_op.add_column(sa.Column('approver', sa.String(length=80), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('outing_requests', schema=None) as batch_op:
        batch_op.drop_column('approver')

    # ### end Alembic commands ###
