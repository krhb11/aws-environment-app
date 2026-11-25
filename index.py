"""Course assignment: Lambda health and DynamoDB integration checks."""
import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path = event.get("rawPath", "/health")
    stage = event.get("requestContext", {}).get("stage", "")
    if stage and stage != "$default" and path.startswith("/" + stage + "/"):
        path = path[len(stage) + 1:]
    request_id = getattr(context, "aws_request_id", "local")
    status = 200
    body = {"status": "ok", "service": "aws-environment-app", "developer_tool": "Codex"}
    if method != "GET" or path not in ("/health", "/storage-check"):
        status, body = 404, {"status": "error", "message": "Not found"}
    elif path == "/storage-check":
        try:
            import boto3
            table = boto3.resource("dynamodb").Table(os.environ["TABLE_NAME"])
            item = {"pk": "environment-check", "checked_at": datetime.now(timezone.utc).isoformat(), "request_id": request_id}
            table.put_item(Item=item)
            saved = table.get_item(Key={"pk": item["pk"]}, ConsistentRead=True).get("Item")
            if saved != item:
                raise RuntimeError("Storage verification mismatch")
            body.update(storage="ok", write="ok", read="ok", item=saved)
        except Exception:
            logger.exception("Storage check failed request_id=%s", request_id)
            status, body = 503, {"status": "error", "storage": "unavailable", "request_id": request_id}
    body["request_id"] = request_id
    logger.info(json.dumps({"request_id": request_id, "path": path, "status": status}))
    return {"statusCode": status, "headers": {"Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store"}, "body": json.dumps(body, ensure_ascii=False)}
