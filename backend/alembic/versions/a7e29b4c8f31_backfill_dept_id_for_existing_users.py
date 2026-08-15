"""Backfill dept_id for existing faculty/student rows

The dev database already had real faculty/student accounts created before
the sub_admin department-scoping change (fbc3e7a91d5c), so they'd otherwise
be left with dept_id = NULL -- invisible to every sub_admin's department-
scoped queries. Only one department (UBIT) exists in any deployment so far,
so this backfill assigns any faculty/student row with a NULL dept_id to it.
A super_admin can reassign individual accounts afterwards if that's ever
wrong; this just prevents accounts from silently falling out of view.

No-op if there isn't exactly one department yet (fresh/empty databases, or
multi-department databases where a guess would be wrong) or if no rows need
it.

Revision ID: a7e29b4c8f31
Revises: fbc3e7a91d5c
Create Date: 2026-08-08

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a7e29b4c8f31'
down_revision: Union[str, None] = 'fbc3e7a91d5c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE users
        SET dept_id = (SELECT id FROM departments)
        WHERE dept_id IS NULL
          AND role IN ('faculty', 'student')
          AND (SELECT COUNT(*) FROM departments) = 1
        """
    )


def downgrade() -> None:
    # Not reversible -- we don't know which rows were NULL before upgrade.
    pass
