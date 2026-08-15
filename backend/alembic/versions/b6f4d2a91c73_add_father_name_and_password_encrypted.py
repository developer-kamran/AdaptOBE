"""Add father_name and password_encrypted to users

father_name is required for student accounts (enforced in schemas/services,
same nullable-at-the-DB-level pattern as enrollment_no/seat_no).

password_encrypted is a Fernet-encrypted copy of the password set at account
creation, added so an authorized admin can view it later from the Edit page.
It is nullable forever -- accounts whose password was set outside app code
(scripts/seed_admin.py, or a direct database update) will never have this
populated, and the frontend must show "not available" for those rather than
erroring. Login is completely unaffected: password_hash (bcrypt) remains the
only column used to authenticate.

Revision ID: b6f4d2a91c73
Revises: a7e29b4c8f31
Create Date: 2026-08-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b6f4d2a91c73'
down_revision: Union[str, None] = 'a7e29b4c8f31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('father_name', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('password_encrypted', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'password_encrypted')
    op.drop_column('users', 'father_name')
