# CLI: clean break at 3.0, keep good flag names

3.0 does not promise v2 invocation compatibility (`python3 gtp.py` / `separate.py` as the product interface). The product entry is the installed/`uv run` **`gtp`** command. Flag *names* that still fit (`-p`/`--path`, `-d` destination, `-s` suffixes, etc.) may be kept where they remain clear; they are not a compatibility contract—rename if a better name appears. `separate.py` is not a second product CLI unless Plan/Apply still need an explicit split helper after redesign.
