import logging
import io
import sys
import unittest
from unittest import mock
from pathlib import Path


class TestLoggingCompat(unittest.TestCase):
    def setUp(self) -> None:
        # Ensure we import the SDK package, not similarly named local modules.
        self._sdk_src = str(Path(__file__).resolve().parents[1] / "src")
        sys.path.insert(0, self._sdk_src)
        import alshival  # noqa: PLC0415
        from alshival.client import get_config  # noqa: PLC0415
        from alshival.logger import refresh_debug_console_handler  # noqa: PLC0415

        cfg = get_config()
        cfg.username = None
        cfg.resource_owner_username = None
        cfg.api_key = None
        cfg.base_url = "https://alshival.ai"
        cfg.portal_prefix = None
        cfg.resource_id = None
        cfg.enabled = True
        cfg.cloud_level = logging.INFO
        cfg.debug = False
        refresh_debug_console_handler()

    def tearDown(self) -> None:
        if sys.path and sys.path[0] == self._sdk_src:
            sys.path.pop(0)

    def test_cloud_level_filters_only_cloud_handler(self) -> None:
        import alshival  # noqa: PLC0415

        alshival.configure(
            username="u",
            api_key="k",
            resource="https://alshival.dev/u/u/resources/r/",
            enabled=True,
            cloud_level=logging.ERROR,
        )

        # Attach a capture handler to verify the log record is still emitted normally.
        capture = []

        class Capture(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:  # noqa: ANN001
                capture.append(record)

        base_logger = alshival.log._logger  # type: ignore[attr-defined]
        cap_h = Capture()
        cap_h.setLevel(logging.DEBUG)
        base_logger.addHandler(cap_h)
        base_logger.setLevel(logging.DEBUG)

        try:
            with mock.patch("requests.Session.post") as post:
                base_logger.propagate = False
                alshival.log.info("hello")
                self.assertEqual(len(capture), 1)
                post.assert_not_called()
        finally:
            base_logger.removeHandler(cap_h)

    def test_debug_method_forwards_when_cloud_level_debug(self) -> None:
        import alshival  # noqa: PLC0415

        root_logger = logging.getLogger()
        original_root_level = root_logger.level
        root_logger.setLevel(logging.WARNING)
        try:
            alshival.configure(
                username="u",
                api_key="k",
                resource="https://alshival.dev/u/u/resources/r/",
                enabled=True,
                cloud_level=logging.DEBUG,
            )
            with mock.patch("requests.Session.post") as post:
                alshival.log.debug("debug event")
                self.assertTrue(post.called)
        finally:
            root_logger.setLevel(original_root_level)

    def test_sdk_debug_mode_prints_to_console_and_forwards_when_possible(self) -> None:
        import alshival  # noqa: PLC0415

        root_logger = logging.getLogger()
        original_root_level = root_logger.level
        root_logger.setLevel(logging.WARNING)
        buf = io.StringIO()
        with mock.patch("sys.stderr", new=buf):
            try:
                alshival.configure(
                    username="u",
                    api_key="k",
                    resource="https://alshival.dev/u/u/resources/r/",
                    enabled=True,
                    debug=True,
                )
                # Keep output focused on SDK logger handlers in this test.
                alshival.log._logger.propagate = False  # type: ignore[attr-defined]
                with mock.patch("requests.Session.post") as post:
                    alshival.log.debug("sdk debug trace")
                    self.assertTrue(post.called)
                self.assertIn("sdk debug trace", buf.getvalue())
            finally:
                root_logger.setLevel(original_root_level)

    def test_attach_is_deduped(self) -> None:
        import alshival  # noqa: PLC0415

        logger = logging.getLogger("test.alshival.dedupe")
        logger.handlers.clear()
        h1 = alshival.attach(logger)
        h2 = alshival.attach(logger)
        self.assertIs(h1, h2)

    def test_resource_id_override_via_kwarg(self) -> None:
        import alshival  # noqa: PLC0415

        alshival.configure(
            username="u",
            api_key="k",
            resource="https://alshival.dev/u/u/resources/r/",
            enabled=True,
            cloud_level=logging.INFO,
        )
        with mock.patch("requests.Session.post") as post:
            alshival.log.error("boom", resource_id="override-r")
            self.assertTrue(post.called)
            args, kwargs = post.call_args
            self.assertIn("/resources/override-r/logs/", args[0])

    def test_cloud_level_disable_token_skips_forwarding(self) -> None:
        import alshival  # noqa: PLC0415

        alshival.configure(
            username="u",
            api_key="k",
            resource="https://alshival.dev/u/u/resources/r/",
            enabled=True,
            cloud_level="false",
        )
        with mock.patch("requests.Session.post") as post:
            alshival.log.error("cloud forwarding disabled")
            post.assert_not_called()

    def test_env_cloud_level_disable_tokens_parse_as_disabled(self) -> None:
        from alshival.client import build_client_config_from_env  # noqa: PLC0415

        with mock.patch.dict("os.environ", {"ALSHIVAL_CLOUD_LEVEL": "false"}, clear=True):
            cfg_false = build_client_config_from_env()
        with mock.patch.dict("os.environ", {"ALSHIVAL_CLOUD_LEVEL": "None"}, clear=True):
            cfg_none = build_client_config_from_env()
        self.assertIsNone(cfg_false.cloud_level)
        self.assertIsNone(cfg_none.cloud_level)

    def test_alert_levels_alias_and_tag_supported(self) -> None:
        import alshival  # noqa: PLC0415

        alshival.configure(
            username="u",
            api_key="k",
            resource="https://alshival.dev/u/u/resources/r/",
            enabled=True,
            cloud_level="ALERTS",
        )
        with mock.patch("requests.Session.post") as post:
            alshival.log.error("below alert threshold")
            post.assert_not_called()

            alshival.log.alert("urgent incident")
            self.assertTrue(post.called)
            _args, kwargs = post.call_args
            payload = kwargs.get("json") or {}
            logs = payload.get("logs") or []
            self.assertTrue(logs)
            self.assertEqual(str(logs[0].get("level") or ""), "alert")

    def test_shared_resource_uses_owner_path_with_actor_headers(self) -> None:
        import alshival  # noqa: PLC0415

        alshival.configure(
            username="viewer-user",
            api_key="k",
            resource="https://alshival.dev/u/owner-user/resources/r/",
            enabled=True,
            cloud_level=logging.INFO,
        )
        with mock.patch("requests.Session.post") as post:
            alshival.log.info("shared write")
            self.assertTrue(post.called)
            args, kwargs = post.call_args
            self.assertIn("/u/owner-user/resources/r/logs/", args[0])
            headers = kwargs.get("headers") or {}
            self.assertEqual(headers.get("x-api-key"), "k")
            self.assertEqual(headers.get("x-user-username"), "viewer-user")
            self.assertNotIn("x-user-email", headers)

    def test_cloud_send_requires_username_identity(self) -> None:
        import alshival  # noqa: PLC0415

        alshival.configure(
            username="",
            api_key="k",
            resource="https://alshival.dev/u/owner-user/resources/r/",
            enabled=True,
            cloud_level=logging.INFO,
        )
        with mock.patch("requests.Session.post") as post:
            alshival.log.info("shared write without username")
            post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
