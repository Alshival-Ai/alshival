import logging
import sys
import unittest
from pathlib import Path


class TestMCPCompat(unittest.TestCase):
    def setUp(self) -> None:
        self._sdk_src = str(Path(__file__).resolve().parents[1] / "src")
        sys.path.insert(0, self._sdk_src)
        import alshival  # noqa: PLC0415
        from alshival.client import get_config  # noqa: PLC0415

        cfg = get_config()
        cfg.username = None
        cfg.email = None
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

    def test_configure_resource_url_parses_owner_uuid_and_prefix(self) -> None:
        import alshival  # noqa: PLC0415
        from alshival.client import get_config  # noqa: PLC0415

        alshival.configure(
            resource="https://alshival.ai/DevTools/u/alshival/resources/3e2ad894-5e5f-4c34-9899-1f9c2158009c/"
        )
        cfg = get_config()
        self.assertEqual(cfg.base_url, "https://alshival.ai")
        self.assertEqual(cfg.portal_prefix, "/DevTools")
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
        self.assertEqual(cfg.resource_owner_username, "alshival")
        self.assertEqual(cfg.resource_id, "3e2ad894-5e5f-4c34-9899-1f9c2158009c")

    def test_mcp_tool_helpers_available(self) -> None:
        import alshival  # noqa: PLC0415

        alshival.configure(username="sam", email="", api_key="secret-key")
        self.assertEqual(alshival.mcp["type"], "mcp")
        self.assertEqual(alshival.mcp["server_label"], "alshival-mcp")
        self.assertEqual(alshival.mcp["headers"]["x-api-key"], "secret-key")
        self.assertEqual(alshival.mcp["headers"]["x-user-username"], "sam")
        self.assertEqual(alshival.mcp.github["server_label"], "github-mcp")
        self.assertIn("server_url", alshival.mcp.github)

    def test_mcp_headers_fall_back_to_email(self) -> None:
        import alshival  # noqa: PLC0415

        alshival.configure(username="", email="sam@example.com", api_key="secret-key")
        headers = alshival.mcp_tool()["headers"]
        self.assertEqual(headers["x-api-key"], "secret-key")
        self.assertEqual(headers["x-user-email"], "sam@example.com")
        self.assertNotIn("x-user-username", headers)


if __name__ == "__main__":
    unittest.main()
