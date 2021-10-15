"""Increase max length of link titles to 200 characters

Revision ID: c5bc94be5b08
Revises: cd39b33b5360
Create Date: 2021-10-15 10:44:02.049628

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c5bc94be5b08'
down_revision = 'cd39b33b5360'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('links', 'title', type_=sa.String(length=200))


def downgrade():
    op.alter_column('links', 'title', type_=sa.String(length=100))
