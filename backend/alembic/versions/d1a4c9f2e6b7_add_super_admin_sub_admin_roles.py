"""Add super_admin/sub_admin roles and dept_id/employee_id to users

Splits the single flat `admin` role into a two-tier hierarchy: super_admin
(manages departments and sub-admins only) and sub_admin (department-scoped
admin managing that department's PLOs, programmes, faculty, students, and
courses). This migration only adds the new Postgres enum labels and the new
user columns; it does not touch existing rows -- that happens in the
follow-up data migration (fbc3e7a91d5c) once the new labels are guaranteed
visible.

Postgres cannot use a freshly-added enum label in the same transaction that
added it, so `ALTER TYPE ... ADD VALUE` runs in its own autocommit block,
separate from the (transactional) column additions below it.

The legacy `admin` enum label is intentionally left in place -- dropping a
Postgres enum label requires rebuilding the whole type, which isn't worth the
risk for one label nothing will assign again after the next migration.

Revision ID: d1a4c9f2e6b7
Revises: c7a2e5d18b30
Create Date: 2026-08-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd1a4c9f2e6b7'
down_revision: Union[str, None] = 'c7a2e5d18b30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'super_admin'")
        op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'sub_admin'")

    op.add_column(
        'users',
        sa.Column('dept_id', sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        'fk_users_dept_id_departments',
        'users', 'departments',
        ['dept_id'], ['id'],
        ondelete='SET NULL',
    )
    op.add_column(
        'users',
        sa.Column('employee_id', sa.String(length=50), nullable=True),
    )
    op.create_unique_constraint('uq_users_employee_id', 'users', ['employee_id'])


def downgrade() -> None:
    op.drop_constraint('uq_users_employee_id', 'users', type_='unique')
    op.drop_column('users', 'employee_id')
    op.drop_constraint('fk_users_dept_id_departments', 'users', type_='foreignkey')
    op.drop_column('users', 'dept_id')
    # Postgres has no DROP VALUE for enum labels, so 'super_admin'/'sub_admin'
    # remain on the type after downgrade -- harmless since nothing references
    # them once the data migration (fbc3e7a91d5c) has also been downgraded.
