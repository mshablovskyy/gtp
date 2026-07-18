# Cross-platform CLI (Windows, macOS, Linux)

The primary product is a CLI that must work for everyday users on Windows, macOS, and Linux. Capture-time restoration must remain system-agnostic enough to support all three; the current `filedate`-based approach is an implementation choice open to better options, but any replacement must keep the same platform set. A GUI is out of scope for the behavioral rewrite unless later adopted as a skin over the same core.
