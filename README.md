# Alshival SDK (Python)

Python logging SDK for sending structured logs to Alshival DevTools resources.

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
- `ALSHIVAL_RESOURCE_ID` (optional, UUID shown on Resource Details)

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
    resource_id=os.getenv("ALSHIVAL_RESOURCE_ID"),
)
```

## Direct SDK Logging

The logger sends events to your resource endpoint:

- `https://alshival.ai/DevTools/u/<username>/resources/<resource_uuid>/logs/`

Basic usage:

```python
import alshival

alshival.log.info("service started")
alshival.log.warning("cache miss", extra={"key": "user:42"})
alshival.log.error("db connection failed")
```

Attach logs to a specific resource per call:

```python
alshival.log.info("one-off event", resource_id="82d7e623-b8ad-4ee6-a047-75bbe587486f")
```

Exception logging:

```python
try:
    1 / 0
except Exception:
    alshival.log.exception("unexpected error")
```

## Python `logging` Integration

Use the SDK as a normal `logging` handler:

```python
import logging
import alshival

alshival.configure(
    username="samuel",
    api_key="your_api_key",
    resource_id="82d7e623-b8ad-4ee6-a047-75bbe587486f",
)

logger = alshival.get_logger("my-service", level=logging.INFO)
logger.info("service online")
logger.error("request failed", extra={"request_id": "abc123"})
```

Attach to an existing logger:

```python
import logging
import alshival

app_logger = logging.getLogger("app")
alshival.attach(app_logger, level=logging.DEBUG)
```

Or use a handler directly:

```python
import logging
import alshival

h = alshival.handler(level=logging.INFO)
root = logging.getLogger()
root.addHandler(h)
```

## Notes

- The SDK is fail-safe by design. Network errors never crash your app.
- If `username`, `api_key`, or `resource_id` is missing, logs are skipped.
- API key can be passed via `ALSHIVAL_API_KEY` or `alshival.configure(...)`.
- TLS verification is on by default (`verify_ssl=True` in `configure`).
