"""Cascade deletes for course and CLO relationships

Deleting a course that had CLOs previously raised a ForeignKeyViolationError
(surfacing as a 500), because clos.course_id and the mapping foreign keys were
created without ON DELETE behaviour. Questions instead lose their tag rather
than being destroyed, so exam records survive a CLO deletion.

Revision ID: b3f1c72d9a41
Revises: ea0d9492afbe
Create Date: 2026-08-05

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b3f1c72d9a41'
down_revision: Union[str, None] = 'ea0d9492afbe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('clos_course_id_fkey', 'clos', type_='foreignkey')
    op.create_foreign_key(
        'clos_course_id_fkey', 'clos', 'courses', ['course_id'], ['id'], ondelete='CASCADE'
    )

    op.drop_constraint('clo_plo_mappings_clo_id_fkey', 'clo_plo_mappings', type_='foreignkey')
    op.create_foreign_key(
        'clo_plo_mappings_clo_id_fkey', 'clo_plo_mappings', 'clos',
        ['clo_id'], ['id'], ondelete='CASCADE',
    )

    op.drop_constraint('clo_plo_mappings_plo_id_fkey', 'clo_plo_mappings', type_='foreignkey')
    op.create_foreign_key(
        'clo_plo_mappings_plo_id_fkey', 'clo_plo_mappings', 'plos',
        ['plo_id'], ['id'], ondelete='CASCADE',
    )

    op.drop_constraint('questions_clo_id_fkey', 'questions', type_='foreignkey')
    op.create_foreign_key(
        'questions_clo_id_fkey', 'questions', 'clos', ['clo_id'], ['id'], ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('questions_clo_id_fkey', 'questions', type_='foreignkey')
    op.create_foreign_key('questions_clo_id_fkey', 'questions', 'clos', ['clo_id'], ['id'])

    op.drop_constraint('clo_plo_mappings_plo_id_fkey', 'clo_plo_mappings', type_='foreignkey')
    op.create_foreign_key(
        'clo_plo_mappings_plo_id_fkey', 'clo_plo_mappings', 'plos', ['plo_id'], ['id']
    )

    op.drop_constraint('clo_plo_mappings_clo_id_fkey', 'clo_plo_mappings', type_='foreignkey')
    op.create_foreign_key(
        'clo_plo_mappings_clo_id_fkey', 'clo_plo_mappings', 'clos', ['clo_id'], ['id']
    )

    op.drop_constraint('clos_course_id_fkey', 'clos', type_='foreignkey')
    op.create_foreign_key('clos_course_id_fkey', 'clos', 'courses', ['course_id'], ['id'])
