"""Canonical institutional reference data for AdaptOBE.

AdaptOBE is deployed for a single department running four degree programs that
share one standard set of ten Programme Learning Outcomes. Those facts are fixed
for this deployment, so they live here as constants rather than being retyped in
seed scripts, tests and documentation.

Note on "shared" PLOs: `plos.program_id` is a foreign key, so each programme owns
its own ten PLO rows (4 x 10 = 40 rows). The *definitions* below are shared; the
rows are per-programme. This is deliberate -- it keeps the CLO-to-PLO mapping
engine's "same programme" scoping intact, and lets a single programme revise its
wording later without disturbing the other three.

PLO wording follows the standard NCEAC / Seoul Accord computing outcomes. Verify
against the department's own OBE manual before treating it as authoritative.
"""

from dataclasses import dataclass
from datetime import date

DEPARTMENT_NAME = (
    "Department of Computer Science "
    "(UBIT - Umaer Basha Institute of Information Technology)"
)
DEPARTMENT_CODE = "UBIT"


@dataclass(frozen=True)
class ProgramSpec:
    code: str
    name: str
    total_semesters: int


@dataclass(frozen=True)
class PLOSpec:
    code: str
    title: str
    description: str
    domain: str


#: The four degree programmes offered by the department.
PROGRAMS: tuple[ProgramSpec, ...] = (
    ProgramSpec(code="BSSE", name="BS Software Engineering", total_semesters=8),
    ProgramSpec(code="BSCS", name="BS Computer Science", total_semesters=8),
    ProgramSpec(code="BSAI", name="BS Artificial Intelligence", total_semesters=8),
    ProgramSpec(code="BSDS", name="BS Data Science", total_semesters=8),
)

#: A student's `seat_no` is `B<2-digit enrollment year><programme code><roll>`
#: (the institution's own numbering scheme, not derived from anything else in
#: this codebase), e.g. `B241101-0007` for a BSSE student who enrolled in
#: 2024. The programme-code segment below is fixed; the year segment is NOT
#: -- see `expected_seat_no_prefix`. Programmes with no configured code are
#: simply not filtered by any of the functions below.
SEAT_NO_PROGRAM_CODES: dict[str, str] = {
    "BSSE": "1101",
    "BSCS": "1100",
    "BSAI": "1102",
    "BSDS": "1103",
}

#: Two semesters per academic year.
SEMESTERS_PER_YEAR = 2


def expected_seat_no_year(semester: int, reference_year: int | None = None) -> int:
    """The 4-digit calendar year a *current-batch* (non-backlog) student in
    `semester` should have originally enrolled, relative to `reference_year`
    (defaults to today's real calendar year -- deliberately not stored on
    the course, so this always reflects "as of right now").

    Two semesters per academic year, so being in semester N means having
    enrolled N // 2 years before the reference year: semester 4 in 2026 ->
    enrolled 2024; semester 8 in 2026 -> enrolled 2022.
    """
    year = reference_year if reference_year is not None else date.today().year
    return year - (semester // 2)


def expected_seat_no_prefix(
    program_code: str, semester: int, reference_year: int | None = None
) -> str | None:
    """The seat-number prefix a current-batch student in this programme and
    semester should have right now, e.g. "B241101" for BSSE/semester 4 in
    2026. None if the programme has no configured seat-number code."""
    code = SEAT_NO_PROGRAM_CODES.get(program_code)
    if code is None:
        return None
    year = expected_seat_no_year(semester, reference_year)
    return f"B{year % 100:02d}{code}"


def seat_no_batch_year(seat_no: str | None) -> int | None:
    """Extract the 4-digit enrollment year encoded in a seat number like
    "B221101-0001" (-> 2022). None if `seat_no` doesn't start with the
    expected `B<2-digit year>` shape at all (rather than guessing)."""
    if not seat_no or len(seat_no) < 3 or seat_no[0] != "B" or not seat_no[1:3].isdigit():
        return None
    return 2000 + int(seat_no[1:3])


def is_backlog_batch_year(seat_no: str | None, semester: int, reference_year: int | None = None) -> bool:
    """True if `seat_no`'s encoded enrollment year is strictly earlier than
    a current-batch student's for this semester -- i.e. this looks like a
    student repeating the course from an earlier cohort. Deliberately not
    programme-scoped: a backlog student may come from any programme in the
    department (see `services/enrollment_import_service.py` and the
    "Add Backlog Student" flow). False for a seat number that doesn't
    parse, since we can't confirm eligibility either way."""
    batch_year = seat_no_batch_year(seat_no)
    if batch_year is None:
        return False
    return batch_year < expected_seat_no_year(semester, reference_year)

#: The ten standard PLOs, seeded identically under every programme.
STANDARD_PLOS: tuple[PLOSpec, ...] = (
    PLOSpec(
        code="PLO-1",
        title="Academic Education",
        description=(
            "Complete an accredited programme of study designed to prepare graduates "
            "as computing professionals, building a strong foundation in mathematics, "
            "computing fundamentals and a computing specialisation."
        ),
        domain="Cognitive",
    ),
    PLOSpec(
        code="PLO-2",
        title="Knowledge for Solving Computing Problems",
        description=(
            "Apply knowledge of computing fundamentals, mathematics and a computing "
            "specialisation to the abstraction and conceptualisation of computing models "
            "from defined problems and requirements."
        ),
        domain="Cognitive",
    ),
    PLOSpec(
        code="PLO-3",
        title="Problem Analysis",
        description=(
            "Identify, formulate, research literature and solve complex computing problems, "
            "reaching substantiated conclusions using fundamental principles of mathematics, "
            "computing sciences and relevant domain disciplines."
        ),
        domain="Cognitive",
    ),
    PLOSpec(
        code="PLO-4",
        title="Design and Development of Solutions",
        description=(
            "Design and evaluate solutions for complex computing problems, and design and "
            "evaluate systems, components and processes that meet specified needs with "
            "appropriate consideration for public health and safety, and cultural, societal "
            "and environmental concerns."
        ),
        domain="Cognitive",
    ),
    PLOSpec(
        code="PLO-5",
        title="Modern Tool Usage",
        description=(
            "Create, select, adapt and apply appropriate techniques, resources and modern "
            "computing tools to complex computing activities, with an understanding of the "
            "limitations of those tools."
        ),
        domain="Psychomotor",
    ),
    PLOSpec(
        code="PLO-6",
        title="Individual and Team Work",
        description=(
            "Function effectively as an individual, and as a member or leader within diverse "
            "teams and in multi-disciplinary settings."
        ),
        domain="Affective",
    ),
    PLOSpec(
        code="PLO-7",
        title="Communication",
        description=(
            "Communicate effectively with the computing community and with society at large "
            "about complex computing activities: comprehending and writing effective reports "
            "and design documentation, making effective presentations, and giving and "
            "understanding clear instructions."
        ),
        domain="Affective",
    ),
    PLOSpec(
        code="PLO-8",
        title="Computing Professionalism and Society",
        description=(
            "Understand and assess societal, health, safety, legal and cultural issues within "
            "the context of professional computing practice, and the consequent "
            "responsibilities that practice carries."
        ),
        domain="Affective",
    ),
    PLOSpec(
        code="PLO-9",
        title="Ethics",
        description=(
            "Understand and commit to professional ethics, responsibilities and the norms of "
            "professional computing practice."
        ),
        domain="Affective",
    ),
    PLOSpec(
        code="PLO-10",
        title="Lifelong Learning",
        description=(
            "Recognise the need for, and have the ability to engage in, independent and "
            "lifelong learning for continual development as a computing professional."
        ),
        domain="Affective",
    ),
)
