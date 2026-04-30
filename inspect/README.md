# Inspect Wrapper

Harbor is the source of truth for this benchmark. The Inspect wrapper loads the
local Harbor dataset through `inspect_harbor` when that package is installed.

Example:

```bash
PYTHONPATH=inspect inspect eval universal_paperclips/prestige.py \
  --model openai/gpt-5
```

