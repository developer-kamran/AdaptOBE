"""Promote existing admin rows to super_admin

Data-only follow-up to d1a4c9f2e6b7. Runs in its own revision because the new
enum labels must be committed (and thus visible) before any statement can
reference them -- this migration is the first one allowed to do that.

Promotes every existing `admin` row to `super_admin` in place, preserving the
account's id/email/password so the bootstrap admin created by
scripts/seed_admin.py keeps working after the split. Safe to re-run: a
second run is a no-op once no `admin` rows remain.

Revision ID: fbc3e7a91d5c
Revises: d1a4c9f2e6b7
Create Date: 2026-08-08

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'fbc3e7a91d5c'
down_revision: Union[str, None] = 'd1a4c9f2e6b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE users SET role = 'super_admin' WHERE role = 'admin'")


def downgrade() -> None:
    op.execute("UPDATE users SET role = 'admin' WHERE role = 'super_admin'")
