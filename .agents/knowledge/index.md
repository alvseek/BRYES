# BRYES Project Knowledge

Project-scoped knowledge for BRYES, gathered across fleet agents (durable facts,
conventions, gotchas). Graduated from the fleet's central store per ADR-010.

Durable **structural** facts live as human-facing docs in [`../../docs/`](../../docs/)
(architecture-overview, agent-loop-flow, python-conventions). Files here carry the
agent-facing facts that are not structural documentation — the ones that cost a session to
rediscover.

| File | Description | Source agent(s) |
|---|---|---|
| [visual-bridge.md](visual-bridge.md) | Windows Bridge and thin JSON client: server-owned targeting, focus, delays and coordinate mapping; local PNG/sidecar files; restart proof, safety limits, rejected capture IDs and next-session procedure alignment. | software-architect |
| [grounding-measurement.md](grounding-measurement.md) | What the Eyes actually hit on the Unreal editor (headers, pins, asset tiles, empty canvas), how to re-measure it with `grounding.py`, and the 4x-crop rule for marking small targets. | software-architect |
| [container-and-keyboard.md](container-and-keyboard.md) | Why the Screen container fails to boot from a CRLF checkout, when it must be rebuilt (`--build`), how keyboard focus actually reaches a window, and how a held key was proved live. | software-architect |
| [procedure-authoring.md](procedure-authoring.md) | One canonical procedure, two generated copies: what the installer rewrites, the ADR link `test_setup.py` pins, the procedure-versus-reference split, and the checks to run after an edit. | software-architect |
