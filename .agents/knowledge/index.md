# BRYES Project Knowledge

Project-scoped knowledge for BRYES, gathered across fleet agents (durable facts,
conventions, gotchas). Graduated from the fleet's central store per ADR-010.

Durable **structural** facts live as human-facing docs in [`../../docs/`](../../docs/)
(architecture-overview, agent-loop-flow, python-conventions). Files here carry the
agent-facing facts that are not structural documentation — the ones that cost a session to
rediscover.

| File | Description | Source agent(s) |
|---|---|---|
| [container-and-keyboard.md](container-and-keyboard.md) | Why the Screen container fails to boot from a CRLF checkout, when it must be rebuilt (`--build`), how keyboard focus actually reaches a window, and how a held key was proved live. | software-architect |
