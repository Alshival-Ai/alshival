# Alshival SDK (Python)

[![Alshival](https://alshival.ai/static/img/logos/brain1_transparent.png)](https://alshival.ai)

Python logging SDK for sending structured logs to Alshival resources (cloud and self-hosted).

## Install

```bash
pip install git+https://github.com/Alshival-Ai/alshival.git@main
```

## Development

For local development:

```bash
python -m pip install -e .
```

Note: if your project has another top-level module/package named `alshival`, Python may import the wrong one. Rename the
conflicting package or adjust your environment so this SDK is the one being imported.

## Usage

To authenticate, create an API key in your Alshival account.

- Sign in to Alshival.
- Open `Account Settings`.
- In the `API Keys` section, create a key (requires an active DevTools subscription).
- Store the key and resource URL in environment variables.

The SDK reads these environment variables automatically:

- `ALSHIVAL_USERNAME` (optional; forwarded as `x-user-username` when set)
- `ALSHIVAL_RESOURCE` (required for cloud logs; full resource URL, auto-derives resource host/path and resource UUID)
- `ALSHIVAL_API_KEY`
- `ALSHIVAL_CLOUD_LEVEL` (optional, defaults to `INFO`; minimum level forwarded to Alshival Cloud Logs: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `ALERT`, `NONE`)

With those set, you can start logging immediately:

```python
import alshival

alshival.log.info("service started")
```

### Cloud Level vs Local Logging

`ALSHIVAL_CLOUD_LEVEL` (or `configure(cloud_level=...)`) controls what gets forwarded to Alshival Cloud Logs.
Accepted values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `ALERT`, `NONE`.
Use `NONE` to disable cloud forwarding.

It does not prevent your logs from being emitted locally via Python's `logging` system. If you want local output,
configure `logging` normally (for example with `logging.basicConfig(...)`).

If you want to override values at runtime, call `configure`:

```python
import os
import alshival

alshival.configure(
    username=os.getenv("ALSHIVAL_USERNAME"),
    api_key=os.getenv("ALSHIVAL_API_KEY"),
    resource=os.getenv("ALSHIVAL_RESOURCE"),
    cloud_level='ERROR',  # only forward ERROR+ to Alshival Cloud Logs
)

alshival.log.info("prints locally; not sent to cloud")
alshival.log.error("prints locally; sent to cloud")
```

Disable cloud forwarding explicitly:

```env
ALSHIVAL_CLOUD_LEVEL=NONE
```

```python
alshival.configure(cloud_level='NONE')
```

## Direct SDK Logging

The logger sends events to your resource endpoint:

- Main site (legacy path): `https://alshival.ai/DevTools/u/<username>/resources/<resource_uuid>/logs/`
- DevTools domain: `https://alshival.dev/u/<username>/resources/<resource_uuid>/logs/`
- Team route: `https://<your-host>/team/<team_name>/resources/<resource_uuid>/logs/`

For shared resources:
- Optionally set `ALSHIVAL_USERNAME` to forward actor identity as `x-user-username`.
- Point `ALSHIVAL_RESOURCE` at the owner's resource URL.
- When `ALSHIVAL_RESOURCE` is set, the SDK derives the endpoint directly from that URL.

You can also provide a full resource URL instead of separate owner/UUID settings:

```env
ALSHIVAL_RESOURCE=https://alshival.dev/u/alshival/resources/3e2ad894-5e5f-4c34-9899-1f9c2158009c/
```

Or a team-scoped resource URL:

```env
ALSHIVAL_RESOURCE=https://selfhost.example/team/devops/resources/3e2ad894-5e5f-4c34-9899-1f9c2158009c/
```

Equivalent runtime override:

```python
alshival.configure(resource="https://alshival.dev/u/alshival/resources/<resource_uuid>/")
```

Basic usage:

```python
import alshival

alshival.log.info("service started")
alshival.log.warning("cache miss", extra={"key": "user:42"})
alshival.log.debug("verbose trace")
alshival.log.error("db connection failed")
alshival.log.alert("pager-worthy incident", extra={"service": "payments"})
```

To forward debug events to cloud logs, set `ALSHIVAL_CLOUD_LEVEL=DEBUG`. To forward only alert events, set
`ALSHIVAL_CLOUD_LEVEL=ALERT`.

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
    resource="https://alshival.dev/u/samuel/resources/82d7e623-b8ad-4ee6-a047-75bbe587486f/",
)

logger = alshival.get_logger("my-service", level=logging.INFO)
logger.info("service online")
logger.error("request failed", extra={"request_id": "abc123"})
logger.log(alshival.ALERT_LEVEL, "high-priority incident detected")

# Shared resource example:
# - your key/identity: username
# - URL path points to the owner's resource URL
alshival.configure(
    username="collaborator-user",
    api_key="your_collaborator_api_key",
    resource="https://alshival.dev/u/owner-user/resources/owner-resource-uuid/",
)
logger.info("shared resource event")
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
- If `api_key` or `resource` target is missing, logs are skipped.
- API key can be passed via `ALSHIVAL_API_KEY` or `alshival.configure(...)`.
- TLS verification is on by default (`verify_ssl=True` in `configure`).
- `404 invalid_resource` usually means the URL owner path and resource UUID do not match.
