"""Seed Role Taxonomy (ADR-010). Level = distance from a typical web-developer profile.

Seed only: entries are discovery hints, never proof of candidate experience.
"""

from app.domain.schemas import RoleTaxonomyEntry

_SEED: dict[int, list[str]] = {
    1: [
        "Backend Developer", "Frontend Developer", "API Developer", "Software Engineer",
        "Web Application Architect", "Technical Lead",
    ],
    2: [
        "Go Developer", "Node.js Developer", "Microservices Engineer", "Integration Engineer",
        "Platform Engineer", "Cloud Application Developer",
    ],
    3: [
        "DevOps Engineer", "Solutions Architect", "SRE", "Database Engineer",
        "QA Automation Engineer", "AI Application Developer", "Technical Product Engineer",
    ],
    4: [
        "Cybersecurity Engineer", "Data Engineer", "Machine Learning Engineer",
        "Technical Consultant", "Engineering Manager", "Technical Project Manager",
    ],
}


def _slug(title: str) -> str:
    return "role_" + title.lower().replace(".", "").replace(" ", "_")


ROLE_TAXONOMY: list[RoleTaxonomyEntry] = [
    RoleTaxonomyEntry(id=_slug(t), title=t, level=lvl) for lvl, ts in _SEED.items() for t in ts
]
