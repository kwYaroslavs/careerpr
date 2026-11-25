"""Offline deterministic stand-in for an LLM, so the whole demo runs without keys."""

import re
from typing import Any, TypeVar

from pydantic import BaseModel

from app.gateway.base import LLMError

T = TypeVar("T", bound=BaseModel)
_STOP = set(
    [
        "the",
        "and",
        "for",
        "with",
        "from",
        "that",
        "this",
        "have",
        "has",
        "you",
        "your",
        "our",
        "are",
        "will",
        "able",
        "work",
        "experience",
        "years",
        "year",
        "team",
        "using",
        "use",
        "used",
        "including",
        "strong",
        "good",
        "knowledge",
        "плюс",
        "опыт",
        "работы",
        "для",
        "или",
        "the",
        "and",
        "на",
        "по",
        "от",
        "и",
        "в",
        "с",
    ]
)
_TOK = re.compile(r"[A-Za-zА-Яа-я0-9+#.]{3,}")


def _tags(line: str, n: int = 4) -> list[str]:
    out: list[str] = []
    for w in _TOK.findall(line):
        lw = w.lower().strip(".")
        if lw not in _STOP and lw not in out:
            out.append(lw)
    return out[:n]


class DemoFakeLLM:
    def complete(self, task: str, schema: type[T], inputs: dict[str, object]) -> T:
        fn = {
            "demo_parse_cv": self._cv,
            "extract_requirements": self._reqs,
            "rewrite_item": self._rewrite,
        }.get(task)
        if fn is None:
            raise LLMError("unavailable", f"fake provider has no handler for {task}")
        return schema.model_validate(fn(inputs))

    @staticmethod
    def _cv(inputs: dict[str, Any]) -> dict[str, Any]:
        lines = [ln.strip(" \t-•*·") for ln in str(inputs["cv_text"]).splitlines() if ln.strip()]
        name = lines[0] if lines else "Candidate"
        text = "\n".join(lines)
        email = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
        phone = re.search(r"\+?\d[\d\s().-]{8,}\d", text)
        contacts = {}
        if email:
            contacts["email"] = email.group(0)
        if phone:
            contacts["phone"] = phone.group(0).strip()
        facts = []
        for ln in lines[1:]:
            if len(ln) < 18 or "@" in ln:
                continue
            low = ln.lower()
            cat = (
                "education"
                if re.search(r"universit|институт|универ|bachelor|master|degree", low)
                else "skill"
                if re.match(r"^(skills|навык|stack|tech)", low)
                else "experience"
            )
            facts.append({"text": ln, "category": cat, "tags": _tags(ln)})
        return {
            "name": name,
            "contacts": contacts,
            "summary": "",
            "facts": facts[:20],
        }

    @staticmethod
    def _reqs(inputs: dict[str, Any]) -> dict[str, Any]:
        lines = [ln.strip(" \t-•*·") for ln in str(inputs["job_description"]).splitlines()]
        reqs = []
        for ln in lines[1:]:
            if len(ln) < 10:
                continue
            low = ln.lower()
            if re.search(r"visa|citizen|relocat|on-?site|work permit|виза|гражданств", low):
                kind = "hard_constraint"
            elif re.search(r"nice|plus|preferred|bonus|будет плюсом|желательно", low):
                kind = "nice"
            else:
                kind = "must"
            reqs.append({"text": ln, "kind": kind, "normalized_skill_ids": _tags(ln)})
        return {"requirements": reqs[:12], "warnings": ["fake provider: heuristic extraction"]}

    @staticmethod
    def _rewrite(inputs: dict[str, Any]) -> dict[str, Any]:
        facts = str(inputs["linked_facts"]).split(":", 1)[0].strip()
        reqs = str(inputs["requirements"]).split(":", 1)[0].strip()
        return {
            "rewritten_text": str(inputs["resume_item"]),
            "fact_ids": [facts],
            "requirement_ids": [reqs],
            "warnings": ["fake provider: text unchanged"],
        }
