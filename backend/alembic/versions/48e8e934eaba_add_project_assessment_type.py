"""Add 'project' to assessment_type enum

Lab and Project move from being `question_type` values to `Assessment.type`
values -- 'lab' already existed there, this adds 'project' alongside it. The
existing 'project'/'lab' `question_type` enum values are unchanged and kept:
a Lab/Project assessment is still made of `Question` rows under the hood
(see app/services/question_service.py), just no longer picked from the
generic "Add Question" type list. See CHANGELOG.md.

Revision ID: 48e8e934eaba
Revises: c3af4f47a354
Create Date: 2026-08-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '48e8e934eaba'
down_revision: Union[str, None] = 'c3af4f47a354'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE cannot run inside the transaction Alembic
    # normally wraps a migration in (PostgreSQL forbids using a brand new
    # enum value in the same transaction that added it, and older PG
    # versions reject the ALTER itself inside a transaction block). Alembic's
    # autocommit_block() runs this statement in its own transaction, same
    # idiom recommended by the Alembic docs for enum additions.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE assessment_type ADD VALUE IF NOT EXISTS 'project'")


def downgrade() -> None:
    # PostgreSQL has no ALTER TYPE ... DROP VALUE. Rebuilding the enum type
    # to remove 'project' would require rewriting every dependent column and
    # is unsafe to do blindly if any assessment already used it, so this
    # downgrade is intentionally a no-op -- consistent with how this project
    # already treats enum values as effectively additive-only (see the
    # `question_type` enum, which has never had a value removed either).
    pass
