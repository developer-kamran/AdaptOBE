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
