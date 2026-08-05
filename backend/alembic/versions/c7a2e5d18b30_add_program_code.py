"""Add a unique code to programs

The institution identifies its degree programmes by short code (BSSE, BSCS,
BSAI, BSDS), matching how departments and courses are already coded. The code
also gives seed scripts a stable idempotency key that does not depend on the
programme's display name.

Added nullable first and backfilled, so the migration is safe on a table that
already holds rows rather than failing on the NOT NULL constraint.

Revision ID: c7a2e5d18b30
Revises: b3f1c72d9a41
Create Date: 2026-08-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c7a2e5d18b30'
down_revision: Union[str, None] = 'b3f1c72d9a41'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('programs', sa.Column('code', sa.String(length=50), nullable=True))

    # Any pre-existing programme gets a placeholder unique code that an admin can
    # rename later; PROG-<id> is guaranteed unique because id is the primary key.
    op.execute("UPDATE programs SET code = 'PROG-' || id WHERE code IS NULL")

    op.alter_column('programs', 'code', nullable=False)
    op.create_unique_constraint('uq_programs_code', 'programs', ['code'])


def downgrade() -> None:
    op.drop_constraint('uq_programs_code', 'programs', type_='unique')
    op.drop_column('programs', 'code')
