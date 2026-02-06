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
