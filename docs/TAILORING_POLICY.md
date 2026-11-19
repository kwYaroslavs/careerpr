# TAILORING_POLICY.md — truthful resume adaptation

## Purpose
Adapt the presentation of a candidate's real experience to a vacancy. Improve relevance and clarity without changing the underlying facts. The system optimizes for a credible, evidence-backed application, not a numerical keyword match.

## Three content layers

### 1. Immutable Fact Base (Master Resume)
The Fact Base is the source of truth for candidate claims:
- employment, roles, dates, companies, projects and responsibilities;
- technologies, tools, methods, certifications and languages;
- measurable outcomes, quantities, percentages, budgets and team sizes;
- leadership, ownership, architecture and management claims;
- education, location, work authorization and other hard constraints.

Every fact has a stable ID, verification status, source/evidence reference, risk tier and (where applicable) approved wording variants.

Rules:
- The LLM may read facts and propose wording, but cannot create, edit, verify or promote facts.
- A fact is not confirmed because the model reports high confidence.
- Missing evidence becomes a clarification question. It is never silently filled.
- The original Master Resume is never overwritten by vacancy-specific tailoring.
- New user-confirmed information is added as a new versioned fact through a domain service.

### 2. Adaptive Framing Layer
The system may propose changes that preserve meaning:
- reorder existing resume items by relevance;
- select an already approved wording variant;
- rewrite an item for clarity and vacancy terminology;
- emphasize evidence that answers a specific requirement;
- adjust summary and section ordering using only supported facts.

Every proposal must identify its target, source fact IDs, relevant requirement IDs, change reason, operation, risk tier and expected document version.

Terminology mapping is allowed only when the candidate's evidence supports equivalence. Example: rephrase "configured CI/CD" as "automated deployment" only when the profile contains the relevant deployment/CI evidence. A skill alias table is a normalization aid, not proof that the candidate used a tool.

### 3. Controlled Gap / Authenticity Buffer
Do not force a perfect-looking match:
- Do not add a missing nice-to-have skill or experience.
- Keep useful adjacent experience when it demonstrates seniority, production ownership, architecture or transferable skills; do not mechanically delete everything absent from the JD.
- A non-core achievement may remain if it is true and adds signal. There is no mandatory quota of 1–2 items.
- Explain a gap in a cover letter or interview note only when the candidate has confirmed the wording and the comparison is fair (e.g. used analogous tool Y, not tool X).
- Never claim "quick to learn", "deep experience" or equivalent unless the candidate approves that statement or it is supported by facts.

### 4. User-approved Stretch layer (ADR-009)
Real job markets expect a CV to be tuned even to tools the candidate has only touched. CareerPR supports **controlled stretching, decided by the user, never by the AI**:
- The AI may only *suggest* a `stretch_candidate` for a requirement marked `stretchable` (adjacent, low-risk tool/skill/methodology).
- The USER approves each stretch individually and writes/accepts the wording plus an `interview_note` ("be ready to answer about X").
- Allowed: soft exposure wording ("familiar with", "hands-on with X in side projects" if the user accepts it), adjacent-tool framing, listing a tool in Skills, terminology matching.
- Forbidden always (never stretchable): numbers/metrics, dates, employers, job titles, degrees, certifications, work authorization/visa, team size, leadership/ownership, and strong wording ("expert", "deep experience") without facts.
- Stretch items carry `verification_status=user_stretch`, show a `stretch` label in review and snapshot, and are listed in the snapshot as an interview-prep checklist.
- No 1:1 matching is needed; a partial match with 1–3 stretches is fine. Never aim for a 100% keyword match.
Responsibility for stretched claims is the user's; the system keeps them bounded, visible and auditable.

### 5. Transferable framing (ADR-013)
- A `transferable` finding links requirement → competence → source Fact IDs. It supports *framing* (R2) such as "Automated deployments with Docker and CI/CD pipelines" for a Platform Engineer vacancy.
- Forbidden: wording that claims direct experience in the new area ("Platform Engineer at …", "built a platform team"), new titles, scope or seniority not in the facts.
- `potential` creates a ClarificationQuestion; an answer becomes a new versioned fact via a domain service. Until then it is not used in the resume.
- `genuine_gap` is shown honestly; only the user-approved Stretch layer (4) may soften low-risk tool/skill gaps.

## Relevance policy
Do not target a fixed 80–90% match score. The product must not calculate or display a percentage match. Use:
- requirement-by-requirement evidence mapping;
- hard-constraint pass/fail;
- Strong / Possible / Stretch / Blocked bucket;
- explicit match categories: direct, transferable, potential, genuine_gap (ADR-011).

A strong application can still have gaps. A 100% keyword match is neither required nor desirable.

## Validation model
Validation must check claims, not merely surface words:
1. Every factual claim in a generated item must be traceable to one or more Fact IDs.
2. Every referenced Fact ID must exist and be eligible for the proposed use.
3. New numbers, dates, companies, roles, technologies, certifications, leadership/ownership claims and hard-constraint claims are blocked unless explicitly supported.
4. Synonyms/aliases are normalized through a reviewed ontology, but alias membership alone does not establish candidate experience.
5. Protected values (identity, contacts, employment dates and company names) must remain unchanged unless a separate user-approved workflow explicitly changes them.
6. Unverifiable or ambiguous output becomes blocked or a ClarificationQuestion; never auto-correct it into a factual claim.

A deterministic validator cannot reliably understand arbitrary natural-language entailment. For ambiguous semantic rewrites, require explicit fact linkage and human review rather than pretending a keyword whitelist proves truth.

## Human review
- AI proposes; deterministic backend validates; human approves.
- High-risk facts (numbers, team size, leadership, ownership, seniority, dates, certifications, work authorization) require individual review.
- Low-risk reorder/wording proposals may be bulk-reviewed only when all validations pass.
- The final exported document must be built from approved changes only.

## Examples
| Source evidence | Allowed adaptation | Forbidden adaptation |
|---|---|---|
| "Configured CI/CD pipelines using GitHub Actions" | "Automated deployment workflows with GitHub Actions" | "Built enterprise DevOps platform" |
| "Used Redis for caching" | "Implemented Redis-based caching" | "Designed distributed caching architecture" unless separately evidenced |
| "Worked with PHP and Symfony" | "Developed Symfony applications in PHP" | Add Laravel, Go or Kubernetes because the vacancy asks for them |
| No Kubernetes evidence | Leave it absent; optionally prepare a confirmed gap note | Add Kubernetes to skills or imply production experience |

## Non-goals
No automatic application submission, keyword stuffing, fabricated match percentages, automatic fact verification, or LLM-controlled approval/snapshot creation.

---
## 🇷🇺 Кратко по-русски
- Факты — неизменяемая основа. ИИ предлагает, backend проверяет, человек одобряет.
- **Слой 4 — Stretch (приукрашивание под контролем пользователя):** можно «немного приврать» про смежные инструменты/навыки (например, «знаком с Terraform», если работали с похожим). Каждый такой пункт ИИ только *предлагает*, а *вы* одобряете вручную и получаете заметку для интервью.
- Нельзя никогда: числа/метрики, даты, работодатели, должности, образование, сертификаты, право на работу, размер команды, лидерство; слова «эксперт/глубокий опыт» без фактов.
- **Категории совпадения:** direct (прямой опыт) · transferable (переносимый) · potential (нужно уточнить) · genuine_gap (реально нет). Переносимый опыт ≠ подтверждённый опыт в новой области (ADR-013).
- Совпадение 1:1 не нужно: 1–3 stretch-пункта на вакансию — нормально. Процент совпадения не показываем.
