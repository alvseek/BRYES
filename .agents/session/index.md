# BRYES Session Log

Episodic work-product for BRYES — one file per theme, newest sub-episode first inside
each. Graduated from the fleet's central store per ADR-010.

| Theme | Agents | Summary |
|---|---|---|
| [bryes-vision-computer-use-agent.md](bryes-vision-computer-use-agent.md) | software-architect | The BRYES build, phase by phase. Latest (2026-07-16 13.53): **Foveal describe + trim (ADR-004) — describe-speed SOLVED (5–16s → ~2s)** by attacking OUTPUT LENGTH not the model (72B boxes in ~1.5s but describes in 5–16s, same frame). OVERVIEW (no focus) = downscaled ×0.5 gist on qwen3-vl-8b; TRIM (focus) = 72B `box()` → crop(+15%) → q3-8b describes the crop; `expect` now requires `focus`. 72B → authoritative Eyes (boxing + `recheck`); ladder q3-8b→recheck→request_diff. Box coords absolute at any res (validated to 4M px). Prior (07-16 09.48): Phase 5 verify-and-recover (ADR-003) — Seam B closed (Eyes report `VERIFICATION`, Brain judges). Earlier: Device interface + real phone (ADR-002, 07-15); shell effector channel (ADR-001, 07-15); Hands natural set + `wait`/`screenshot` → Tokopedia (07-14); VLM describe + atomic `type` + qwen3.6-flash bake-off (07-13); Phases 1–4 + 1024 diagnosis (07-11). |
