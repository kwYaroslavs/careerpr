# ROADMAP.md
The implementation backlog is decomposed into small AI-executable cards in `tasks/README.md`.

Milestones:
- M0 — verified scaffold, contracts, persistence and offline gateway.
- M1 — complete evidence-based tailoring pipeline and PDF snapshot on FakeLLM.
- M2 — real provider and user workspace.
- M3 — acceptance on three real vacancies; tag `mvp-0`.
- MVP-1 — import, richer fact verification, clarification and tracker.

Career adaptation (ADR-010..013): T-031 (contracts) in M0/M1; T-032–T-036 in MVP-1; T-037 UI after. Expanded Match is the default mode.

Order is dependency order. Take exactly one card per AI session/PR. Read only that card's listed docs and files. The product policy is in `TAILORING_POLICY.md`.

Walking skeleton first: deterministic fixtures and fake provider before live LLM. Do not implement multiple cards in one AI request.
