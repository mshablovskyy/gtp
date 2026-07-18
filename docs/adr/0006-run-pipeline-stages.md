# Run pipeline: Discover → Parse → Match → Plan → Apply

A Run is five stages: **Discover** (walk Source tree → Sidecars + Media + Album), **Parse** (Sidecar → title + Capture time), **Match** (Sidecar ↔ Media), **Plan** (pure intended actions: copy targets, times, Unprocessed reasons), **Apply** (copy, set times, logs). Logic stages are side-effect-free and testable; Apply owns I/O. New capability extends or inserts a stage only when needed—not speculative empty stages. Dry-run and reports can stop after Plan without reimplementing Match.
