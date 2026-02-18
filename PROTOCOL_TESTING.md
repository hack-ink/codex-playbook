# Protocol Testing Methodology

This document defines a repeatable test suite for the Main/Assistant/Coding protocol in `AGENTS.md`.

## 1) Preconditions

1. Sync runtime config and schemas into `~/.codex/` (copy/symlink from this repo).
2. Confirm runtime files are updated:
   - `rg -n 'routing_mode|slice_id|relay_via_main|attempt|coding_subtask_ids|parallel_peak_inflight|main_router' ~/.codex/AGENTS.md ~/.codex/dispatch-preflight.schema.json ~/.codex/agent-output.assistant.write.schema.json ~/.codex/agent-output.assistant.read_only.schema.json ~/.codex/agent-output.coding.schema.json`

Pass criteria:
- All required fields above are present in runtime files.
- Legacy routing labels do not appear in runtime protocol/schema files.

## 2) Schema Validation (Structural)

Run:

```sh
python3 - <<'PY'
import json
from pathlib import Path
from jsonschema import Draft202012Validator
files = [
  'dispatch-preflight.schema.json',
  'agent-output.assistant.write.schema.json',
  'agent-output.assistant.read_only.schema.json',
  'agent-output.coding.schema.json',
]
for f in files:
    d = json.loads(Path(f).read_text())
    Draft202012Validator.check_schema(d)
    v = Draft202012Validator(d)
    bad = []
    for i, ex in enumerate(d.get('examples', []), 1):
        errs = list(v.iter_errors(ex))
        if errs:
            bad.append((i, [e.message for e in errs]))
    print(f'{f}:', 'OK' if not bad else f'INVALID {bad}')
PY
```

Pass criteria:
- All four files return `OK`.

## 3) E2E Positive Test (`main_router`)

Method:
1. Create two independent sandbox files.
2. Main delegates write subtask to Assistant.
3. Assistant provides coding briefs and review plan.
4. Main relays two Coding spawns in parallel (`wait-any` + replenish).
5. Each coding completion is immediately routed to Assistant for review.

Pass criteria:
- Assistant write output: `status="done"`, `blocked=false`.
- `routing_mode="main_router"`.
- `relay_via_main=true`.
- `parallel_peak_inflight >= 2`.
- `coding_subtask_ids` non-empty.
- Every referenced coding payload is schema-valid and includes required fields (`summary`, `self_check.command`, `self_check.evidence`).
- Main does not finalize completion before Assistant review verdict.

## 4) Negative Tests

### A) Assistant direct write refusal

Method:
- Ask Assistant to edit a file directly without Coding dispatch.

Pass criteria:
- Assistant returns `status="awaiting_review"`, `blocked=true`.
- File remains unchanged.

### B) Invalid Coding parent

Method:
- Spawn Coding with `[PARENT:MAIN]` instead of `[PARENT:MAIN_ROUTER]`.

Pass criteria:
- Blocked result with concrete routing violation reason.

### C) Invalid routing mode

Method:
- Feed output payload with `routing_mode != "main_router"`.

Pass criteria:
- Schema or runtime checks reject the payload.

### D) Schema-incomplete coding payload

Method:
- Provide Assistant a coding payload missing required coding-schema fields (for example missing `summary` or `self_check.command`).

Pass criteria:
- Assistant returns `status="awaiting_review"`, `blocked=true`.
- `blocking_reason` indicates coding output schema invalidity.

## 5) Concurrency Limit Test

Method:
1. Spawn `N` assistants that sleep and return JSON.
2. Increase `N` until spawn fails.
3. Record first failure.
4. Close completed agents and retry.

Expected:
- Failure at configured thread limit (currently observed: 24).
- Completed agents hold slots until `close_agent`.
- New spawn succeeds after close.

## 6) Wait-Any Test

Method:
1. Spawn probes with delays (e.g. 10s, 20s, 30s).
2. Call `wait` on all ids repeatedly.

Pass criteria:
- Early completion returns first when polled in time.
- No forced wait-all behavior while runnable work remains.

## 7) Result Recording Template

```json
{
  "run_id": "protocol-test-YYYYMMDD-HHMM",
  "schema_validation": "pass|fail",
  "routing_mode_selected": "main_router",
  "e2e_main_router": "pass|fail",
  "negative_assistant_direct_write": "pass|fail",
  "negative_invalid_coding_parent": "pass|fail",
  "negative_invalid_routing_mode": "pass|fail",
  "negative_schema_incomplete_coding_payload": "pass|fail",
  "concurrency_limit_observed": 24,
  "wait_any_verified": true,
  "notes": []
}
```

## 8) Cleanup

- Remove temporary test artifacts and close remaining test agents.
