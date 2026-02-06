# Alshival SDK (Python)

Minimal client for sending logs to Alshival.

## Install

```bash
pip install alshival
```

## Usage

```python
import os
import alshival

alshival.configure(
    username=os.getenv("ALSHIVAL_USERNAME"),
    api_key=os.getenv("ALSHIVAL_API_KEY"),
)

try:
    1 / 0
except Exception as e:
    alshival.log.error(f"error: {e}")
```

## Environment variables

- `ALSHIVAL_USERNAME`
- `ALSHIVAL_API_KEY`
- `ALSHIVAL_BASE_URL` (optional, default: `https://alshival.ai`)

## Notes

- API keys are sent to `/api/logs/ingest/`.
- Errors are swallowed by default to avoid breaking client apps.
