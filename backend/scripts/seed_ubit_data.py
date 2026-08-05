"""Seed the UBIT department, its four degree programmes, and their PLOs.

Creates 1 department, 4 programmes (BSSE / BSCS / BSAI / BSDS) and 40 PLO rows
(the 10 standard outcomes under each programme), generating a 384-dimensional
`all-MiniLM-L6-v2` embedding for every PLO so the CLO-to-PLO mapping engine has
something to match against immediately.

Idempotent: re-running reconciles instead of duplicating. Existing rows are
matched by their unique codes, and a PLO's embedding is only regenerated when
its wording actually changed -- so a repeat run costs no model inference.

Usage (from backend/, with the venv active):
    python scripts/seed_ubit_data.py
    python scripts/seed_ubit_data.py --force-embeddings   # recompute every vector
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.database import AsyncSessionLocal, engine  # noqa: E402
from app.core.institution import (  # noqa: E402
    DEPARTMENT_CODE,
    DEPARTMENT_NAME,
    PROGRAMS,
    STANDARD_PLOS,
)
from app.ml import embeddings  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.plo import PLO  # noqa: E402
from app.models.program import Program  # noqa: E402
from app.services.plo_service import build_embedding_source  # noqa: E402

# DEBUG=true builds the engine with echo=True, which would bury this script's
# progress output in SQL. Echo ignores logger levels, so switch it off directly.
engine.echo = False


async def _upsert_department(db: AsyncSession) -> tuple[Department, str]:
    result = await db.execute(select(Department).where(Department.code == DEPARTMENT_CODE))
    department = result.scalar_one_or_none()

    if department is None:
        department = Department(name=DEPARTMENT_NAME, code=DEPARTMENT_CODE)
        db.add(department)
        await db.flush()
        return department, "created"

    if department.name != DEPARTMENT_NAME:
        department.name = DEPARTMENT_NAME
        return department, "updated"

    return department, "unchanged"


async def _upsert_programs(db: AsyncSession, department: Department) -> tuple[dict[str, Program], dict[str, int]]:
    codes = [spec.code for spec in PROGRAMS]
    result = await db.execute(select(Program).where(Program.code.in_(codes)))
    existing = {program.code: program for program in result.scalars().all()}

    programs: dict[str, Program] = {}
    counts = {"created": 0, "updated": 0, "unchanged": 0}

    for spec in PROGRAMS:
        program = existing.get(spec.code)
        if program is None:
            program = Program(
                dept_id=department.id,
                code=spec.code,
                name=spec.name,
                total_semesters=spec.total_semesters,
            )
            db.add(program)
            counts["created"] += 1
        elif (
            program.name != spec.name
            or program.total_semesters != spec.total_semesters
            or program.dept_id != department.id
        ):
            program.dept_id = department.id
            program.name = spec.name
            program.total_semesters = spec.total_semesters
            counts["updated"] += 1
        else:
            counts["unchanged"] += 1

        programs[spec.code] = program

    await db.flush()
    return programs, counts


def _encode_plo_texts(needed: set[str]) -> dict[str, list[float]]:
    """Encode each distinct PLO text once, not once per programme.

    The ten outcomes are identical across all four programmes, so encoding per
    PLO row would run the model 40 times to produce 10 distinct vectors.
    """
    if not needed:
        return {}

    print(f"Encoding {len(needed)} distinct PLO text(s) with {embeddings.MODEL_NAME}...")
    return {text: embeddings.encode_text(text) for text in sorted(needed)}


def _needs_embedding(plo: PLO | None, spec, force: bool) -> bool:
    if force or plo is None or plo.embedding is None:
        return True
    return plo.title != spec.title or plo.description != spec.description


async def _upsert_plos(
    db: AsyncSession, programs: dict[str, Program], force_embeddings: bool
) -> dict[str, int]:
    program_ids = [program.id for program in programs.values()]
    result = await db.execute(select(PLO).where(PLO.program_id.in_(program_ids)))
    existing = {(plo.program_id, plo.code): plo for plo in result.scalars().all()}

    # First pass: work out which distinct texts actually need encoding, so an
    # unchanged re-run performs no model inference at all.
    needed_texts = {
        build_embedding_source(spec.title, spec.description)
        for program in programs.values()
        for spec in STANDARD_PLOS
        if _needs_embedding(existing.get((program.id, spec.code)), spec, force_embeddings)
    }
    vectors = _encode_plo_texts(needed_texts)

    counts = {"created": 0, "updated": 0, "unchanged": 0}
    for spec in STANDARD_PLOS:
        text = build_embedding_source(spec.title, spec.description)
        for program in programs.values():
            plo = existing.get((program.id, spec.code))

            if plo is None:
                db.add(
                    PLO(
                        program_id=program.id,
                        code=spec.code,
                        title=spec.title,
                        description=spec.description,
                        domain=spec.domain,
                        embedding=vectors[text],
                    )
                )
                counts["created"] += 1
                continue

            changed = False
            if _needs_embedding(plo, spec, force_embeddings):
                plo.embedding = vectors[text]
                changed = True
            if plo.title != spec.title or plo.description != spec.description:
                plo.title = spec.title
                plo.description = spec.description
                changed = True
            if plo.domain != spec.domain:
                plo.domain = spec.domain
                changed = True

            counts["updated" if changed else "unchanged"] += 1

    await db.flush()
    return counts


async def seed(force_embeddings: bool = False) -> None:
    async with AsyncSessionLocal() as db:
        department, dept_status = await _upsert_department(db)
        print(f"Department {DEPARTMENT_CODE}: {dept_status} (id={department.id})")

        programs, program_counts = await _upsert_programs(db, department)
        print(
            "Programmes: "
            f"{program_counts['created']} created, "
            f"{program_counts['updated']} updated, "
            f"{program_counts['unchanged']} unchanged "
            f"({', '.join(programs)})"
        )

        plo_counts = await _upsert_plos(db, programs, force_embeddings)
        print(
            "PLOs: "
            f"{plo_counts['created']} created, "
            f"{plo_counts['updated']} updated, "
            f"{plo_counts['unchanged']} unchanged "
            f"({len(STANDARD_PLOS)} outcomes x {len(PROGRAMS)} programmes)"
        )

        await db.commit()
        print("Seed complete.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed the UBIT department, degree programmes and standard PLOs."
    )
    parser.add_argument(
        "--force-embeddings",
        action="store_true",
        help="Regenerate every PLO embedding even if the wording is unchanged.",
    )
    args = parser.parse_args()

    asyncio.run(seed(force_embeddings=args.force_embeddings))


if __name__ == "__main__":
    main()
