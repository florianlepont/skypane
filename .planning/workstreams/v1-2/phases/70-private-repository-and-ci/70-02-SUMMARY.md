# Plan 70-02 summary: manual deploy proof

Done on 2026-11-25 by the owner, guided step by step. Evidence in `70-EVIDENCE.md`.

- Secrets confirmed at repository level (names only); a dedicated CI deploy key installed on the server and set as `DEPLOY_SSH_PRIVATE_KEY`; the old CI key line removed after the first success; local private copy deleted.
- `deploy.yml` refused a wrong confirmation (run 45712777893) and a ref other than main (run 45712969497), and deployed successfully twice (runs 45713258859 and 45713738451), the second with only the dedicated key.
- The live frame stayed online with the same flight, picture and settings; a battery reading change (83 % to 92 %) is recorded and watched.
- Owner decision: dedicated-key-only; the write-access limitation is handed to the security audit.
- No follow-up plan 70-02b is needed.
