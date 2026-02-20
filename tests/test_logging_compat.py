import logging
import sys
import unittest
from unittest import mock


class TestLoggingCompat(unittest.TestCase):
    def setUp(self) -> None:
        # Ensure we import the SDK package, not the Django app at repo root.
        sys.path.insert(0, "Packages/alshival/src")

    def tearDown(self) -> None:
        if sys.path and sys.path[0] == "Packages/alshival/src":
            sys.path.pop(0)

    def test_cloud_level_filters_only_cloud_handler(self) -> None:
        import alshival  # noqa: PLC0415

        alshival.configure(username="u", api_key="k", resource_id="r", enabled=True, cloud_level=logging.ERROR)

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

    def test_attach_is_deduped(self) -> None:
        import alshival  # noqa: PLC0415

        logger = logging.getLogger("test.alshival.dedupe")
        logger.handlers.clear()
        h1 = alshival.attach(logger)
        h2 = alshival.attach(logger)
        self.assertIs(h1, h2)

    def test_resource_id_override_via_kwarg(self) -> None:
        import alshival  # noqa: PLC0415

        alshival.configure(username="u", api_key="k", resource_id="r", enabled=True, cloud_level=logging.INFO)
        with mock.patch("requests.Session.post") as post:
            alshival.log.error("boom", resource_id="override-r")
            self.assertTrue(post.called)
            args, kwargs = post.call_args
            self.assertIn("/resources/override-r/logs/", args[0])

    def test_alert_level_and_tag_supported(self) -> None:
        import alshival  # noqa: PLC0415

        alshival.configure(username="u", api_key="k", resource_id="r", enabled=True, cloud_level="ALERT")
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


if __name__ == "__main__":
    unittest.main()
