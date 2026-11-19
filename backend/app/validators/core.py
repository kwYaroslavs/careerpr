"""Deterministic validators (no LLM). See docs/LLM_CONTRACTS.md. MVP-0: V1,V2,V3,V5,V6,V7."""

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from app.domain.schemas import ChangeProposal, Fact, Operation, ProposalStatus, Resume


@dataclass
class Violation:
    code: str
    message: str


@dataclass
class ValidationContext:
    resume: Resume
    facts: list[Fact]
    vocabulary: set[str] = field(default_factory=set)  # allowed entities
    other_companies: set[str] = field(default_factory=set)  # tracker companies (V7)

    @property
    def fact_ids(self) -> set[str]:
        return {f.id for f in self.facts}

    @property
    def item_ids(self) -> set[str]:
        return {i.id for i in self.resume.items}


_NUM = re.compile(r"\d+(?:[.,]\d+)?")
_WORDNUM = {"one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
            "twenty", "thirty", "forty", "fifty", "hundred", "thousand", "million", "percent"}
_PLACEHOLDER = re.compile(r"\[[A-Za-z _]+\]|\{\{.*?\}\}|\bTODO\b|\bTBD\b|lorem ipsum", re.I)
_CAPS = re.compile(r"\b[A-Z][A-Za-z0-9+#.]{1,}\b")


def _numbers(text: str) -> set[str]:
    nums = {n.replace(",", ".") for n in _NUM.findall(text)}
    return nums | {w for w in re.findall(r"[a-z]+", text.lower()) if w in _WORDNUM}


def v1_refs(p: ChangeProposal, c: ValidationContext) -> list[Violation]:
    out = []
    target = next((item for item in c.resume.items if item.id == p.target_id), None)
    if target is None:
        out.append(Violation("V1", f"unknown target_id {p.target_id}"))
    else:
        if p.before != target.text:
            out.append(Violation("V1", "before text does not match the current target"))
    if p.expected_version != c.resume.version:
        out.append(
            Violation(
                "V1",
                f"stale proposal version: expected {p.expected_version}, current {c.resume.version}",
            )
        )
    missing = set(p.fact_ids) - c.fact_ids
    if missing:
        out.append(Violation("V1", f"unknown fact_ids {sorted(missing)}"))
    if p.operation not in set(Operation):
        out.append(Violation("V1", f"operation not whitelisted: {p.operation}"))
    return out


def v2_no_new_numbers(p: ChangeProposal, c: ValidationContext) -> list[Violation]:
    allowed = _numbers(p.before)
    for f in c.facts:
        if f.id in p.fact_ids:
            allowed |= _numbers(f.text)
    new = _numbers(p.after) - allowed
    return [Violation("V2", f"new numbers/quantities: {sorted(new)}")] if new else []


def v3_no_new_entities(p: ChangeProposal, c: ValidationContext) -> list[Violation]:
    known = {w.lower() for w in c.vocabulary}
    source_entities = _CAPS.findall(p.before)
    for f in c.facts:
        if f.id in p.fact_ids:
            source_entities.extend(_CAPS.findall(f.text))
    known |= {w.lower() for w in source_entities}
    known_acronyms = {w.lower() for w in source_entities if w.isupper()}
    words = p.after.split()
    first = words[0].strip(".,;:").lower() if words else ""  # sentence-initial caps is grammar
    new = {
        w
        for w in _CAPS.findall(p.after)
        if w.lower() not in known
        and w.lower() != first
        and not any(
            w.lower() == entity + "ful"
            for entity in known_acronyms
        )
    }
    return [Violation("V3", f"new entities: {sorted(new)}")] if new else []


def v5_protected_unchanged(p: ChangeProposal, c: ValidationContext) -> list[Violation]:
    return [
        Violation("V5", f"protected value '{k}' altered")
        for k, v in c.resume.protected.items()
        if v in p.before and v not in p.after
    ]


def v6_no_placeholders(p: ChangeProposal, c: ValidationContext) -> list[Violation]:
    return [Violation("V6", "placeholder found")] if _PLACEHOLDER.search(p.after) else []


def v7_no_company_leak(p: ChangeProposal, c: ValidationContext) -> list[Violation]:
    hit = [n for n in c.other_companies if n.lower() in p.after.lower()]
    return [Violation("V7", f"other company named: {hit}")] if hit else []


VALIDATORS: dict[str, Callable[[ChangeProposal, ValidationContext], list[Violation]]] = {
    "V1": v1_refs,
    "V2": v2_no_new_numbers,
    "V3": v3_no_new_entities,
    "V5": v5_protected_unchanged,
    "V6": v6_no_placeholders,
    "V7": v7_no_company_leak,
}


def run_validators(p: ChangeProposal, c: ValidationContext) -> ChangeProposal:
    """Return a copy with validators_passed set and status=blocked on violations. Pure."""
    violations: list[Violation] = []
    passed: list[str] = []
    for code, fn in VALIDATORS.items():
        v = fn(p, c)
        violations += v
        if not v:
            passed.append(code)
    update: dict[str, object] = {"validators_passed": passed}
    if violations:
        update["status"] = ProposalStatus.BLOCKED
        update["blocked_reason"] = "; ".join(f"{v.code}: {v.message}" for v in violations)
    return p.model_copy(update=update)
