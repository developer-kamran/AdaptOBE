"""Institutional reference data and the UBIT seed routine.

The seed tests exercise the same upsert helpers the script uses, driven through
the transactional test session so nothing is written to the developer's database.
"""

import dataclasses
import sys
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import delete, func, select

from app.core import institution
from app.ml import embeddings
from app.models.department import Department
from app.models.plo import PLO
from app.models.program import Program

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from seed_ubit_data import _upsert_department, _upsert_plos, _upsert_programs  # noqa: E402

EXPECTED_PROGRAM_CODES = {"BSSE", "BSCS", "BSAI", "BSDS"}
VALID_DOMAINS = {"Cognitive", "Psychomotor", "Affective"}


class TestInstitutionConstants:
    def test_department_identifies_ubit(self):
        assert institution.DEPARTMENT_CODE == "UBIT"
        assert "UBIT" in institution.DEPARTMENT_NAME

    def test_exactly_four_programs_with_expected_codes(self):
        assert len(institution.PROGRAMS) == 4
        assert {p.code for p in institution.PROGRAMS} == EXPECTED_PROGRAM_CODES

    def test_program_codes_are_unique(self):
        codes = [p.code for p in institution.PROGRAMS]
        assert len(codes) == len(set(codes))

    def test_exactly_ten_standard_plos(self):
        assert len(institution.STANDARD_PLOS) == 10

    def test_plo_codes_are_sequential_and_unique(self):
        codes = [p.code for p in institution.STANDARD_PLOS]
        assert codes == [f"PLO-{n}" for n in range(1, 11)]

    def test_every_plo_has_substantive_text(self):
        for spec in institution.STANDARD_PLOS:
            assert spec.title.strip()
            # Descriptions feed the embedding model, so a stub would quietly
            # degrade CLO-to-PLO suggestion quality.
            assert len(spec.description.strip()) > 40, spec.code

    def test_every_plo_has_a_valid_bloom_domain(self):
        for spec in institution.STANDARD_PLOS:
            assert spec.domain in VALID_DOMAINS, spec.code

    def test_specs_are_immutable(self):
        """Frozen dataclasses stop a caller mutating shared reference data."""
        with pytest.raises(dataclasses.FrozenInstanceError):
            institution.STANDARD_PLOS[0].title = "changed"


@pytest_asyncio.fixture
async def clean_institution(db_session):
    """Remove any already-seeded UBIT rows inside the test transaction.

    A developer's database will normally have the real seed applied, which would
    otherwise make "created" counts depend on whether the script had been run.
    The surrounding fixture rolls this back, so live data is untouched.
    """
    department = (
        await db_session.execute(
            select(Department).where(Department.code == institution.DEPARTMENT_CODE)
        )
    ).scalar_one_or_none()

    if department is not None:
        program_ids = list(
            (
                await db_session.execute(
                    select(Program.id).where(Program.dept_id == department.id)
                )
            )
            .scalars()
            .all()
        )
        if program_ids:
            # plos -> programs -> departments: no ON DELETE cascade on these FKs.
            await db_session.execute(delete(PLO).where(PLO.program_id.in_(program_ids)))
            await db_session.execute(delete(Program).where(Program.id.in_(program_ids)))
        await db_session.execute(
            delete(Department).where(Department.id == department.id)
        )
        await db_session.flush()

    return db_session


@pytest.mark.usefixtures("clean_institution")
class TestSeed:
    async def test_seed_creates_department_programs_and_all_plos(self, db_session):
        department, status = await _upsert_department(db_session)
        assert status == "created"

        programs, counts = await _upsert_programs(db_session, department)
        assert counts["created"] == 4
        assert set(programs) == EXPECTED_PROGRAM_CODES

        plo_counts = await _upsert_plos(db_session, programs, force_embeddings=False)
        assert plo_counts["created"] == 40  # 10 outcomes x 4 programmes

        total = await db_session.execute(
            select(func.count())
            .select_from(PLO)
            .where(PLO.program_id.in_([p.id for p in programs.values()]))
        )
        assert total.scalar() == 40

    async def test_seeded_plos_have_384_dim_embeddings(self, db_session):
        department, _ = await _upsert_department(db_session)
        programs, _ = await _upsert_programs(db_session, department)
        await _upsert_plos(db_session, programs, force_embeddings=False)

        result = await db_session.execute(
            select(PLO).where(PLO.program_id == programs["BSSE"].id)
        )
        plos = list(result.scalars().all())

        assert len(plos) == 10
        for plo in plos:
            assert plo.embedding is not None, plo.code
            assert len(plo.embedding) == embeddings.EMBEDDING_DIM

    async def test_re_running_the_seed_does_not_duplicate_rows(self, db_session):
        department, _ = await _upsert_department(db_session)
        programs, _ = await _upsert_programs(db_session, department)
        await _upsert_plos(db_session, programs, force_embeddings=False)

        # Second pass over the same database.
        department, dept_status = await _upsert_department(db_session)
        programs, program_counts = await _upsert_programs(db_session, department)
        plo_counts = await _upsert_plos(db_session, programs, force_embeddings=False)

        assert dept_status == "unchanged"
        assert program_counts == {"created": 0, "updated": 0, "unchanged": 4}
        assert plo_counts == {"created": 0, "updated": 0, "unchanged": 40}

        program_total = await db_session.execute(
            select(func.count()).select_from(Program).where(Program.dept_id == department.id)
        )
        assert program_total.scalar() == 4

    async def test_seed_repairs_edited_plo_wording(self, db_session):
        department, _ = await _upsert_department(db_session)
        programs, _ = await _upsert_programs(db_session, department)
        await _upsert_plos(db_session, programs, force_embeddings=False)

        result = await db_session.execute(
            select(PLO).where(PLO.program_id == programs["BSCS"].id, PLO.code == "PLO-1")
        )
        plo = result.scalar_one()
        plo.description = "Drifted description that no longer matches the standard."
        await db_session.flush()

        plo_counts = await _upsert_plos(db_session, programs, force_embeddings=False)

        assert plo_counts["updated"] == 1
        assert plo_counts["unchanged"] == 39

        await db_session.refresh(plo)
        assert plo.description == institution.STANDARD_PLOS[0].description

    async def test_plos_are_scoped_per_program(self, db_session):
        """Each programme owns its own PLO rows, which keeps mapping suggestions
        scoped to a single programme."""
        department, _ = await _upsert_department(db_session)
        programs, _ = await _upsert_programs(db_session, department)
        await _upsert_plos(db_session, programs, force_embeddings=False)

        for code in EXPECTED_PROGRAM_CODES:
            result = await db_session.execute(
                select(func.count()).select_from(PLO).where(PLO.program_id == programs[code].id)
            )
            assert result.scalar() == 10, code
