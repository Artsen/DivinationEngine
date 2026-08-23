# Agent invariants

1. No AI belongs in the divination core.
2. Never fabricate interpretations or correspondences.
3. All externally sourced meaning preserves Source provenance and exact text boundaries.
4. Drawing and placement are separate operations.
5. Saved casts are immutable historical results and are never regenerated on read.
6. Production casting uses cryptographically secure OS randomness.
7. Tests use injected deterministic randomness.
8. I Ching is six three-coin throws, persisted bottom line first.
9. Keep API, application/domain, and persistence responsibilities separated.
10. A future AI is a client of this system, never part of its truth source.
11. Corpus imports remain transactional and idempotent; they never imply deletion.
12. Stable external import keys are identities and must not be casually changed.
13. Context may deterministically select relevance but may never fabricate meaning.
14. Every knowledge provenance ID returned by context must be resolvable in that response.
15. Continuing a deck session cannot redraw an item already consumed in that session.
16. Open content taxonomies must not be unnecessarily hard-coded as DB checks.

Do not add canonical-seeming corpus data without a documented, rights-compatible Source.
