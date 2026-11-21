from app.domain.schemas import (
    ChangeProposal,
    Fact,
    Operation,
    Resume,
    ResumeItem,
    RiskTier,
)
from app.validators import ValidationContext, run_validators

BEFORE = "Led a team of 5 engineers from 2020 to 2022, improving performance by 30%."


def _ctx() -> ValidationContext:
    resume = Resume(
        id="r1",
        items=[ResumeItem(id="i1", text=BEFORE)],
        protected={},
    )
    facts = [
        Fact(
            id="f1",
            text=("Led a team of 5 engineers from 2020 to 2022, improving performance by 30%."),
        )
    ]
    return ValidationContext(resume=resume, facts=facts, other_companies=set())


def _p(after: str, fact_ids: list[str] | None = None) -> ChangeProposal:
    if fact_ids is None:
        fact_ids = ["f1"]
    return ChangeProposal(
        id="p1",
        run_id="run1",
        target_id="i1",
        operation=Operation.REWRITE,
        risk_tier=RiskTier.R2,
        before=BEFORE,
        after=after,
        change_reason="refining numbers and dates",
        fact_ids=fact_ids,
        expected_version=1,
    )


def test_v2_allowed_existing_numbers_and_dates() -> None:
    # Rephrasing keeping same numbers/dates/percentages
    after = "Managed 5 software engineers during 2020-2022, boosting speed by 30%."
    r = run_validators(_p(after), _ctx())
    assert r.status == "pending"
    assert "V2" in r.validators_passed


def test_v2_blocked_new_number() -> None:
    # Introducing a new number (10) not in before or facts
    after = "Led a team of 10 engineers from 2020 to 2022, improving performance by 30%."
    r = run_validators(_p(after), _ctx())
    assert r.status == "blocked"
    assert "V2" in (r.blocked_reason or "")


def test_v2_blocked_new_percentage() -> None:
    # Introducing 50% instead of 30%
    after = "Led a team of 5 engineers from 2020 to 2022, improving performance by 50%."
    r = run_validators(_p(after), _ctx())
    assert r.status == "blocked"
    assert "V2" in (r.blocked_reason or "")


def test_v2_blocked_new_date_year() -> None:
    # Introducing year 2024 not present in facts or before
    after = "Led a team of 5 engineers from 2020 to 2024, improving performance by 30%."
    r = run_validators(_p(after), _ctx())
    assert r.status == "blocked"
    assert "V2" in (r.blocked_reason or "")


def test_v2_blocked_new_word_number() -> None:
    # Introducing word number "ten" not in facts or before
    after = "Led a team of ten engineers from 2020 to 2022, improving performance by 30%."
    r = run_validators(_p(after), _ctx())
    assert r.status == "blocked"
    assert "V2" in (r.blocked_reason or "")


def test_v2_decimal_and_currency_protection() -> None:
    resume = Resume(
        id="r2",
        items=[ResumeItem(id="i2", text="Saved $1.5M in cloud costs.")],
    )
    facts = [Fact(id="f2", text="Saved $1.5M in cloud costs.")]
    ctx = ValidationContext(resume=resume, facts=facts)

    # Same decimal/currency passes
    p_ok = ChangeProposal(
        id="p2",
        run_id="run1",
        target_id="i2",
        operation=Operation.REWRITE,
        risk_tier=RiskTier.R2,
        before="Saved $1.5M in cloud costs.",
        after="Optimized architecture and saved $1.5M in cloud costs.",
        change_reason="clarity",
        fact_ids=["f2"],
        expected_version=1,
    )
    assert run_validators(p_ok, ctx).status == "pending"

    # New decimal $2.5M fails
    p_bad = ChangeProposal(
        id="p3",
        run_id="run1",
        target_id="i2",
        operation=Operation.REWRITE,
        risk_tier=RiskTier.R2,
        before="Saved $1.5M in cloud costs.",
        after="Saved $2.5M in cloud costs.",
        change_reason="amplification",
        fact_ids=["f2"],
        expected_version=1,
    )
    r_bad = run_validators(p_bad, ctx)
    assert r_bad.status == "blocked"
    assert "V2" in (r_bad.blocked_reason or "")
