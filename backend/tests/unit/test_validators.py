from app.domain.schemas import ChangeProposal, Fact, Operation, Resume, ResumeItem, RiskTier
from app.validators import ValidationContext, run_validators

BEFORE = "Built REST APIs with PHP and Symfony."


def _ctx() -> ValidationContext:
    resume = Resume(
        id="r1",
        items=[ResumeItem(id="i1", text=BEFORE)],
        protected={"email": "a@b.com"},
    )
    facts = [Fact(id="f1", text="Built REST APIs with PHP and Symfony")]
    return ValidationContext(resume=resume, facts=facts, other_companies={"Acme"})


def _p(after: str, target_id: str = "i1") -> ChangeProposal:
    return ChangeProposal(
        id="p1",
        run_id="run1",
        target_id=target_id,
        operation=Operation.REWRITE,
        risk_tier=RiskTier.R2,
        before=BEFORE,
        after=after,
        change_reason="clarity",
        fact_ids=["f1"],
        expected_version=1,
    )


def test_clean_rewrite_passes() -> None:
    r = run_validators(_p("Designed RESTful APIs with PHP and Symfony."), _ctx())
    assert r.status == "pending" and r.blocked_reason is None


def test_new_number_blocked() -> None:
    r = run_validators(_p("Built REST APIs with PHP and Symfony, improving speed by 40%."), _ctx())
    assert r.status == "blocked" and "V2" in (r.blocked_reason or "")


def test_new_entity_blocked() -> None:
    r = run_validators(_p("Built REST APIs with PHP and Kubernetes."), _ctx())
    assert "V3" in (r.blocked_reason or "")


def test_placeholder_and_leak_blocked() -> None:
    r = run_validators(_p("Built APIs for [Company] and Acme."), _ctx())
    assert "V6" in (r.blocked_reason or "") and "V7" in (r.blocked_reason or "")


def test_unknown_target_blocked() -> None:
    r = run_validators(_p("Built REST APIs.", target_id="nope"), _ctx())
    assert "V1" in (r.blocked_reason or "")


def test_input_not_mutated() -> None:
    p = _p("Built REST APIs with PHP and Kubernetes.")
    run_validators(p, _ctx())
    assert p.status == "pending"


def test_acronym_adjective_is_not_treated_as_a_new_entity() -> None:
    r = run_validators(_p("Designed RESTful APIs with PHP and Symfony."), _ctx())
    assert "V3" not in (r.blocked_reason or "")


def test_stale_resume_version_is_blocked() -> None:
    p = _p("Built REST APIs with PHP and Symfony.")
    p.expected_version = 0
    r = run_validators(p, _ctx())
    assert r.status == "blocked" and "stale proposal version" in (r.blocked_reason or "")


def test_before_must_match_current_target() -> None:
    p = _p("Built REST APIs with PHP and Symfony.")
    p.before = "A different source sentence."
    r = run_validators(p, _ctx())
    assert r.status == "blocked" and "before text" in (r.blocked_reason or "")
