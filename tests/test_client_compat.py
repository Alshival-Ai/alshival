import logging
import os
import sys
import unittest
from pathlib import Path
from unittest import mock


class TestClientCompat(unittest.TestCase):
    def setUp(self) -> None:
        self._sdk_src = str(Path(__file__).resolve().parents[1] / "src")
        sys.path.insert(0, self._sdk_src)
        from alshival.client import get_config  # noqa: PLC0415

        cfg = get_config()
        cfg.username = None
        cfg.resource_base_url = None
        cfg.resource_logs_prefix = None
        cfg.api_key = None
        cfg.resource_id = None
        cfg.enabled = True
        cfg.cloud_level = logging.INFO

    def tearDown(self) -> None:
        if sys.path and sys.path[0] == self._sdk_src:
            sys.path.pop(0)

    def test_configure_resource_url_parses_user_route(self) -> None:
        import alshival  # noqa: PLC0415
        from alshival.client import get_config  # noqa: PLC0415

        alshival.configure(resource="https://alshival.ai/DevTools/u/alshival/resources/abc-123/")
        cfg = get_config()
        self.assertEqual(cfg.resource_base_url, "https://alshival.ai")
        self.assertEqual(cfg.resource_logs_prefix, "/DevTools/u/alshival/resources")
        self.assertEqual(cfg.resource_id, "abc-123")

    def test_configure_resource_url_accepts_logs_suffix(self) -> None:
        import alshival  # noqa: PLC0415
        from alshival.client import get_config  # noqa: PLC0415

        alshival.configure(resource="https://alshival.dev/u/alshival/resources/r-123/logs/")
        cfg = get_config()
        self.assertEqual(cfg.resource_base_url, "https://alshival.dev")
        self.assertEqual(cfg.resource_logs_prefix, "/u/alshival/resources")
        self.assertEqual(cfg.resource_id, "r-123")

    def test_configure_resource_url_parses_team_route(self) -> None:
        import alshival  # noqa: PLC0415
        from alshival.client import get_config  # noqa: PLC0415

        alshival.configure(resource="https://selfhost.example/team/devops/resources/r-123/")
        cfg = get_config()
        self.assertEqual(cfg.resource_base_url, "https://selfhost.example")
        self.assertEqual(cfg.resource_logs_prefix, "/team/devops/resources")
        self.assertEqual(cfg.resource_id, "r-123")

    def test_resource_endpoint_prefers_parsed_resource_prefix(self) -> None:
        import alshival  # noqa: PLC0415
        from alshival.client import build_resource_logs_endpoint  # noqa: PLC0415

        alshival.configure(resource="https://dev.alshival.dev/team/Starwood/resources/5176/")
        endpoint = build_resource_logs_endpoint("override-r")
        self.assertEqual(
            endpoint,
            "https://dev.alshival.dev/team/Starwood/resources/override-r/logs/",
        )

    def test_resource_endpoint_empty_without_resource_context(self) -> None:
        from alshival.client import build_resource_logs_endpoint  # noqa: PLC0415

        endpoint = build_resource_logs_endpoint("r-123")
        self.assertEqual(endpoint, "")

    def test_env_resource_url_wins_and_base_url_env_ignored(self) -> None:
        from alshival.client import build_client_config_from_env  # noqa: PLC0415

        with mock.patch.dict(
            os.environ,
            {
                "ALSHIVAL_BASE_URL": "https://ignored.example",
                "ALSHIVAL_RESOURCE": "https://alshival.dev/u/owner-user/resources/r-123/",
            },
            clear=False,
        ):
            cfg = build_client_config_from_env()

        self.assertEqual(cfg.resource_base_url, "https://alshival.dev")
        self.assertEqual(cfg.resource_logs_prefix, "/u/owner-user/resources")
        self.assertEqual(cfg.resource_id, "r-123")


if __name__ == "__main__":
    unittest.main()
