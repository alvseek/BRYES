# BRYES Session Log

Episodic work-product for BRYES — one file per theme, newest sub-episode first inside
each. Graduated from the fleet's central store per ADR-010.

| Theme | Agents | Summary |
|---|---|---|
| [bryes-vision-computer-use-agent.md](bryes-vision-computer-use-agent.md) | software-architect | The BRYES build, phase by phase. Latest (2026-07-16): **Phase 5 verify-and-recover (ADR-003) — Seam B closed**; change-feedback is the VLM's job (Eyes report `VERIFICATION: <state>`, Brain judges) + Brain-gated 2-image diff + advisory recovery. Two over-builds killed by measurement: the screen-wide pixel no-op (a typed digit scores below the noise floor; UI-TARS can't box → `framediff.py` parked) and the VLM pass/fail verdict (noisy → report-not-judge). Earlier: Device interface + real phone (ADR-002, 07-15); shell effector channel (ADR-001, 07-15); Hands natural set + `wait`/`screenshot` → Tokopedia (07-14); VLM describe + atomic `type` + qwen3.6-flash bake-off (07-13); Phases 1–4 + 1024 diagnosis (07-11). |
