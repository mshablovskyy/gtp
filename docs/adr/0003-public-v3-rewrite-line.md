# Public same-repo v3 rewrite line

GTP stays one public repo (`mshablovskyy/gtp`). **`main` remains the stable v2 line** people get by default. The behavioral rewrite is developed on a long-lived public branch (e.g. `rewrite/v3`); day-to-day work is short-lived branches merged into that line via PRs. Cutover to `main` is a deliberate **3.0** release/merge when ready—not continuous replacement of `main` during the rewrite. A separate private repo for the rewrite was rejected: same product, no secrets-driven need, and it would split history/issues for no gain.
