import importlib.util
import json
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("app", Path(__file__).parent / "index.py")
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class HandlerTests(unittest.TestCase):
    def invoke(self, path, method="GET"):
        return app.handler({"rawPath": path, "requestContext": {"http": {"method": method}}}, types.SimpleNamespace(aws_request_id="test-request"))

    def test_health(self):
        response = self.invoke("/health")
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(json.loads(response["body"])["developer_tool"], "Codex")

    def test_rejects_unknown_path_and_method(self):
        self.assertEqual(self.invoke("/unknown")["statusCode"], 404)
        self.assertEqual(self.invoke("/health", "POST")["statusCode"], 404)

    def test_named_stage_prefix(self):
        response = app.handler({"rawPath": "/dev/health", "requestContext": {"stage": "dev", "http": {"method": "GET"}}}, None)
        self.assertEqual(response["statusCode"], 200)

    def test_storage_round_trip(self):
        class Table:
            def put_item(self, Item): self.item = Item
            def get_item(self, **kwargs):
                self.key, self.consistent = kwargs["Key"], kwargs["ConsistentRead"]
                return {"Item": self.item}
        table = Table()
        fake = types.SimpleNamespace(resource=lambda service: types.SimpleNamespace(Table=lambda name: table))
        with patch.dict(sys.modules, {"boto3": fake}), patch.dict(os.environ, {"TABLE_NAME": "test-table"}):
            response = self.invoke("/storage-check")
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(json.loads(response["body"])["storage"], "ok")
        self.assertEqual(table.key, {"pk": "environment-check"})
        self.assertTrue(table.consistent)

    def test_storage_failure_hides_internal_error(self):
        fake = types.SimpleNamespace(resource=lambda service: (_ for _ in ()).throw(RuntimeError("private-error")))
        with patch.dict(sys.modules, {"boto3": fake}):
            response = self.invoke("/storage-check")
        self.assertEqual(response["statusCode"], 503)
        self.assertNotIn("private-error", response["body"])


if __name__ == "__main__": unittest.main()
