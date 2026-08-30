# Deferred Items — Phase 06.3

Out-of-scope items discovered during execution, logged per the executor's scope-boundary rule (not fixed).

## 06.3-02

- **`server/test_poll_loop.py` pinned-digest check fails**: "a default config against the FLIGHT1 fixture reproduces the pinned pre-06-10 panel.bin digest" fails (`ea555e8b...` != pinned `45b17a3e...`). This is in `server/plane/render.py`'s panel image pipeline (physical frame rendering), a completely different subsystem from `companion/static/style.css` (this plan's only file). Confirmed pre-existing: `git diff be1ed44 5686900 --stat -- server/` is empty, so none of this plan's three commits touched anything under `server/`. `STATE.md`'s own history already documents an independent `_DEFAULT_CONFIG_DIGEST` re-pin landing on `main` from the illustration-placement debug session ("real pixel output moved, not a platform artifact this time") — this is very likely that same unresolved re-pin surfacing here. Not fixed by this plan; belongs to whichever phase/task owns `server/plane/render.py`'s digest pinning.
