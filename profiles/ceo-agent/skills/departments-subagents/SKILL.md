---
name: departments-subagents
description: "Run the CEO's department subagents on demand."
version: 1.0.0
author: Jordan (tradersurfer), Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [delegation, subagents, departments, ceo, northstar]
    category: autonomous-ai-agents
---

# Department Subagents

Runs the eleven department subagents that were spawned in the JECI-Gang group
chat on 2026-10-01/02 — same names, same goals, same leaf role, same
inherit-the-parent-toolsets behaviour. The CEO agent does not execute this work
itself; it dispatches and supervises.

The engine lives at `departments-subagents/` inside the CEO profile
(`$HERMES_HOME/profiles/ceo-agent/departments-subagents/`).

## When to Use

- The CEO agent is asked to run a department ("run the tech workstream",
  "spin up the field ops analysts").
- A prior JECI-Gang analysis needs re-running against updated diligence facts.
- Never for a single ad-hoc question — that is a plain `delegate_task` call.

## Roster

| Subagent | Department | Focus |
|---|---|---|
| `chief-of-staff` | ceo-agent | Executive audit trail, decision gates, interlocks |
| `strategy-analyst` | ceo-agent | Service-line mix, market position, synergies |
| `decision-risk-analyst` | ceo-agent | 17-problem risk register, 3 scenarios |
| `tech-architecture-lead` | cto-agent | KEEP/REPLACE/INTEGRATE/AUTOMATE/DEFER, SOR per domain |
| `crm-data-lead` | cto-agent | 4 overlapping DBs, system of record, migration |
| `automation-analyst` | cto-agent | Quick wins vs long-term, effort/EBITDA scoring |
| `security-iam-lead` | cto-agent | SSO/RBAC, 38K records, PCI, 90-day IAM roadmap |
| `field-operations-analyst` | coo-agent | Field-ops assessment, math shown |
| `dispatch-scheduling-analyst` | coo-agent | Dispatch/scheduling assessment |
| `sop-process-analyst` | coo-agent | Process/SOP by financial value and friction |
| `customer-experience-analyst` | coo-agent | NPS/CSAT, churn, repeat rate, service recovery |

## How to Run

From an active turn, build the payload and make one `delegate_task` call:

```python
import sys
sys.path.insert(0, r"C:\Users\jorda\AppData\Local\hermes\profiles\ceo-agent\departments-subagents")
from engine import dispatch_plan

plan = dispatch_plan("cto-agent")     # or dispatch_plan() for all eleven
```

`plan["arguments"]["tasks"]` goes straight into `delegate_task`. Do not rewrite
the goals — they are the session's wording. `plan["roster"]` and
`plan["instructions"]` are paste-ready text for the response.

Outside Python, read the payload directly:

```bash
python "$HERMES_HOME/profiles/ceo-agent/departments-subagents/engine.py" cto-agent
python "$HERMES_HOME/profiles/ceo-agent/departments-subagents/engine.py" list
```

For handle-level supervision (status / wait / cancel / result) use
`DepartmentRunner` — it goes through the public
`agent.subagent_lifecycle` service and fails closed outside an agent turn.

## Pitfalls

- **Do not import `tools.delegate_tool`.** The engine renders payloads for the
  parent's `delegate_task` call; child construction stays on the host-owned
  path. Only `DepartmentRunner` touches the lifecycle service, and only that.
- **`correlation_id` defaults to the subagent name** and is unique per parent
  session — relaunching the same subagent in one session raises
  `SubagentLifecycleError`. Pass a distinct id to retry.
- **The lifecycle service retains results in-process for one hour.** Anything
  that must survive a restart goes through `delegate_task` background
  completion or `cronjob`, not `DepartmentRunner`.
- **Model pinning is inherited.** The session ran every subagent on the
  parent's resolved model; `spec.model` is `None` everywhere by design. Set it
  per spec only when a department genuinely needs a different model.
- **No `working_directory` override.** Hermes delegates use isolated task
  environments and the request API rejects a cwd.

## Verification

```bash
cd "$HERMES_HOME/profiles/ceo-agent/departments-subagents"
python engine.py list                     # 11 subagents, 3 departments
python engine.py coo-agent | python -c "import json,sys; print(len(json.load(sys.stdin)['arguments']['tasks']))"   # 4
```

The department count must match the roster table above: ceo-agent 3,
cto-agent 4, coo-agent 4.
