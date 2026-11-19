# AGENTPR_SPEC.md — proposal lifecycle
`pending → (validators) → blocked | pending-review → approved | rejected | edited → applied`
- Created per `run_id`; unique `dedupe_key`; carries `expected_version`.
- Approve applies a patch via `services.apply_proposal` (pure function, returns new doc version). Conflict on version → status `conflict`, UI rebase.
- Re-running a run never overwrites approved/edited/rejected proposals; only fills missing ones.
- Bulk approve allowed for `low` risk only. `high` risk facts: individually.
- Every transition writes an AuditEvent.
- Generic design: AgentPR must not import CareerPR domain types (future extraction as separate lib): operations are data (`target_id, operation, before, after`).
