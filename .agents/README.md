# `.agents/` — Fleet-Authored Work-Product Memory

This folder holds **work-product memory** for the BRYES project, graduated out of the
authoring fleet's central memory store and into this repo per
[ADR-010](https://github.com/) (work-product memory localization). Any AI agent working
in this repo can **read and extend** it.

## Layout

- **`session/`** — episodic session history. One file per theme; each `### [date]`
  sub-episode is a past working session (what happened, decisions, tech debts, next
  steps). See [`session/index.md`](session/index.md).
- **`knowledge/`** — project-scoped knowledge gathered across agents (durable facts,
  conventions, gotchas specific to BRYES). See [`knowledge/index.md`](knowledge/index.md).

## Provenance

Each sub-episode header carries `(agent: <domain>)` — the fleet agent that authored it.
When multiple agents worked the same theme, their sub-episodes are stacked (newest-first)
in one file; knowledge from multiple agents is concatenated under `## <agent>` headings.

## What is intentionally NOT here

Agent **identity** memory stays with the fleet, never in this repo: reasoning patterns,
emotional memory, RAS triggers, general (cross-project) knowledge, and any
business/strategy/relationship context. This folder is *what the agents did on BRYES*,
not *who the agents are*.

## Structural docs live elsewhere

Human-facing architecture/orientation lives in [`../docs/`](../docs/) (orientation map +
structural context). `.agents/` is the agent-facing lane; `docs/` is the human-facing lane.
