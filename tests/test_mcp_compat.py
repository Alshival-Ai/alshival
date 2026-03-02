import logging
import os
import sys
import unittest
from unittest import mock
from pathlib import Path


class TestMCPCompat(unittest.TestCase):
    def setUp(self) -> None:
        self._sdk_src = str(Path(__file__).resolve().parents[1] / "src")
        sys.path.insert(0, self._sdk_src)
        import alshival  # noqa: PLC0415
        from alshival.client import get_config  # noqa: PLC0415

        cfg = get_config()
        cfg.username = None
        cfg.resource_route_kind = None
        cfg.resource_route_value = None
        cfg.resource_logs_prefix = None
        cfg.resource_owner_username = None
        cfg.api_key = None
        cfg.base_url = "https://alshival.ai"
        cfg.portal_prefix = None
        cfg.resource_id = None
        cfg.enabled = True
        cfg.cloud_level = logging.INFO

    def tearDown(self) -> None:
        if sys.path and sys.path[0] == self._sdk_src:
            sys.path.pop(0)

    def test_resource_endpoint_legacy_host_uses_devtools_prefix(self) -> None:
        import alshival  # noqa: PLC0415
        from alshival.client import build_resource_logs_endpoint  # noqa: PLC0415

        alshival.configure(base_url="https://alshival.ai", portal_prefix=None)
        endpoint = build_resource_logs_endpoint("sam", "abc-123")
        self.assertEqual(
            endpoint,
            "https://alshival.ai/DevTools/u/sam/resources/abc-123/logs/",
        )

    def test_resource_endpoint_devtools_domain_uses_root_paths(self) -> None:
        import alshival  # noqa: PLC0415
        from alshival.client import build_resource_logs_endpoint  # noqa: PLC0415

        alshival.configure(base_url="https://alshival.dev", portal_prefix=None)
        endpoint = build_resource_logs_endpoint("sam", "abc-123")
        self.assertEqual(
            endpoint,
            "https://alshival.dev/u/sam/resources/abc-123/logs/",
        )

    def test_resource_endpoint_respects_explicit_prefix_override(self) -> None:
        import alshival  # noqa: PLC0415
        from alshival.client import build_resource_logs_endpoint  # noqa: PLC0415

        alshival.configure(base_url="https://alshival.ai", portal_prefix="")
        endpoint = build_resource_logs_endpoint("sam", "abc-123")
        self.assertEqual(
            endpoint,
            "https://alshival.ai/u/sam/resources/abc-123/logs/",
        )

    def test_resource_endpoint_supports_team_route(self) -> None:
        import alshival  # noqa: PLC0415
        from alshival.client import build_resource_logs_endpoint  # noqa: PLC0415

        alshival.configure(base_url="https://alshival.dev", portal_prefix=None)
        endpoint = build_resource_logs_endpoint("devops", "abc-123", route_kind="team")
        self.assertEqual(
            endpoint,
            "https://alshival.dev/team/devops/resources/abc-123/logs/",
        )

    def test_configure_resource_url_parses_owner_uuid_and_prefix(self) -> None:
        import alshival  # noqa: PLC0415
        from alshival.client import get_config  # noqa: PLC0415

        alshival.configure(
            resource="https://alshival.ai/DevTools/u/alshival/resources/3e2ad894-5e5f-4c34-9899-1f9c2158009c/"
        )
        cfg = get_config()
        self.assertEqual(cfg.base_url, "https://alshival.ai")
        self.assertEqual(cfg.portal_prefix, "/DevTools")
        self.assertEqual(cfg.resource_route_kind, "u")
        self.assertEqual(cfg.resource_route_value, "alshival")
        self.assertEqual(cfg.resource_logs_prefix, "/DevTools/u/alshival/resources")
        self.assertEqual(cfg.resource_owner_username, "alshival")
        self.assertEqual(cfg.resource_id, "3e2ad894-5e5f-4c34-9899-1f9c2158009c")

    def test_configure_resource_url_accepts_logs_suffix(self) -> None:
        import alshival  # noqa: PLC0415
        from alshival.client import get_config  # noqa: PLC0415

        alshival.configure(
            resource="https://alshival.dev/u/alshival/resources/3e2ad894-5e5f-4c34-9899-1f9c2158009c/logs/"
        )
        cfg = get_config()
        self.assertEqual(cfg.base_url, "https://alshival.dev")
        self.assertEqual(cfg.portal_prefix, "")
        self.assertEqual(cfg.resource_route_kind, "u")
        self.assertEqual(cfg.resource_route_value, "alshival")
        self.assertEqual(cfg.resource_logs_prefix, "/u/alshival/resources")
        self.assertEqual(cfg.resource_owner_username, "alshival")
        self.assertEqual(cfg.resource_id, "3e2ad894-5e5f-4c34-9899-1f9c2158009c")

    def test_configure_resource_url_parses_team_route(self) -> None:
        import alshival  # noqa: PLC0415
        from alshival.client import get_config  # noqa: PLC0415

        alshival.configure(
            resource="https://selfhost.example/team/devops/resources/3e2ad894-5e5f-4c34-9899-1f9c2158009c/"
        )
        cfg = get_config()
        self.assertEqual(cfg.base_url, "https://selfhost.example")
        self.assertEqual(cfg.portal_prefix, "")
        self.assertEqual(cfg.resource_route_kind, "team")
        self.assertEqual(cfg.resource_route_value, "devops")
        self.assertEqual(cfg.resource_logs_prefix, "/team/devops/resources")
        self.assertEqual(cfg.resource_owner_username, "devops")
        self.assertEqual(cfg.resource_id, "3e2ad894-5e5f-4c34-9899-1f9c2158009c")

    def test_resource_endpoint_prefers_parsed_resource_prefix(self) -> None:
        import alshival  # noqa: PLC0415
        from alshival.client import build_resource_logs_endpoint  # noqa: PLC0415

        alshival.configure(
            resource="https://dev.alshival.dev/team/Starwood/resources/517616d5-4513-4d19-a59e-0e5d052f46b5/"
        )
        endpoint = build_resource_logs_endpoint("ignored-user", "override-r")
        self.assertEqual(
            endpoint,
            "https://dev.alshival.dev/team/Starwood/resources/override-r/logs/",
        )

    def test_env_resource_url_wins_over_conflicting_base_url(self) -> None:
        from alshival.client import build_client_config_from_env  # noqa: PLC0415

        with mock.patch.dict(
            os.environ,
            {
                "ALSHIVAL_BASE_URL": "https://alshival.ai",
                "ALSHIVAL_RESOURCE": "https://alshival.dev/u/owner-user/resources/r-123/",
            },
            clear=False,
        ):
            cfg = build_client_config_from_env()

        self.assertEqual(cfg.base_url, "https://alshival.dev")
        self.assertEqual(cfg.portal_prefix, "")
        self.assertEqual(cfg.resource_route_kind, "u")
        self.assertEqual(cfg.resource_route_value, "owner-user")
        self.assertEqual(cfg.resource_logs_prefix, "/u/owner-user/resources")
        self.assertEqual(cfg.resource_owner_username, "owner-user")
        self.assertEqual(cfg.resource_id, "r-123")

    def test_mcp_tool_helpers_available(self) -> None:
        import alshival  # noqa: PLC0415

        alshival.configure(username="sam", api_key="secret-key")
        self.assertEqual(alshival.mcp["type"], "mcp")
        self.assertEqual(alshival.mcp["server_label"], "alshival-mcp")
        self.assertEqual(alshival.mcp["headers"]["x-api-key"], "secret-key")
        self.assertEqual(alshival.mcp["headers"]["x-user-username"], "sam")
        self.assertNotIn("x-user-email", alshival.mcp["headers"])
        self.assertEqual(alshival.mcp.github["server_label"], "github-mcp")
        self.assertIn("server_url", alshival.mcp.github)

    def test_mcp_headers_with_missing_username_omit_user_header(self) -> None:
        import alshival  # noqa: PLC0415

        alshival.configure(username="", api_key="secret-key")
        headers = alshival.mcp_tool()["headers"]
        self.assertEqual(headers["x-api-key"], "secret-key")
        self.assertNotIn("x-user-username", headers)
        self.assertNotIn("x-user-email", headers)


if __name__ == "__main__":
    unittest.main()
