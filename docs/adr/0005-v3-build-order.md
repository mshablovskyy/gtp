# v3 build order

Rewrite work merges to `rewrite/v3` in this order: (0) kickoff docs, (1) package skeleton **and** agreed Run architecture, (2) fixtures, (3) read + Match, (4) copy + Capture time + logs, (5) parity check against v2 on real Takeout, (6) new features. Architecture is decided at skeleton time so modules match the pipeline; features wait until behavioral parity.
