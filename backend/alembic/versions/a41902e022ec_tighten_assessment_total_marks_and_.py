"""Tighten assessment total_marks and question marks to greater than zero

Revision ID: a41902e022ec
Revises: 2e8ce4e237b9
Create Date: 2026-08-19 16:38:26.979042

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a41902e022ec'
down_revision: Union[str, None] = '2e8ce4e237b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Autogenerate doesn't diff CHECK constraint bodies, only presence by
    # name -- both constraints already existed as `>= 0`, so this has to be
    # hand-written as drop-and-recreate under the same name.
    op.drop_constraint("ck_assessment_total_marks", "assessments", type_="check")
    op.create_check_constraint(
        "ck_assessment_total_marks", "assessments", "total_marks > 0"
    )
    op.drop_constraint("ck_question_marks", "questions", type_="check")
    op.create_check_constraint("ck_question_marks", "questions", "marks > 0")


def downgrade() -> None:
    op.drop_constraint("ck_assessment_total_marks", "assessments", type_="check")
    op.create_check_constraint(
        "ck_assessment_total_marks", "assessments", "total_marks >= 0"
    )
    op.drop_constraint("ck_question_marks", "questions", type_="check")
    op.create_check_constraint("ck_question_marks", "questions", "marks >= 0")
