# Alshival SDK (Python)

Minimal client for sending logs to Alshival.

## Install

```bash
pip install git+https://github.com/Alshival-Ai/alshival.git@main
```

## Usage

To authenticate, create an API key in your Alshival account.

- Sign in to Alshival.
- Open `Account Settings`.
- In the `API Keys` section, create a key (requires an active DevTools subscription).
- Store the key and your username in environment variables.

The SDK reads these environment variables automatically:

- `ALSHIVAL_USERNAME`
- `ALSHIVAL_API_KEY`
- `ALSHIVAL_BASE_URL` (optional, defaults to `https://alshival.ai`)

With those set, you can start logging immediately:

```python
import alshival

alshival.log.info("service started")
```

If you want to override values at runtime, call `configure`:

```python
import os
import alshival

alshival.configure(
    username=os.getenv("ALSHIVAL_USERNAME"),
    api_key=os.getenv("ALSHIVAL_API_KEY"),
    base_url=os.getenv("ALSHIVAL_BASE_URL", "https://alshival.ai"),
)
```

## Cloud Logs

The logger sends events to Alshival Cloud Logs over HTTPS.

Example:

```python
import alshival

alshival.log.info("service started")

try:
    1 / 0
except Exception:
    alshival.log.exception("unexpected error")
```

```python
import alshival

try:
    1 / 0
except Exception as e:
    alshival.log.error(f"error: {e}")
```
