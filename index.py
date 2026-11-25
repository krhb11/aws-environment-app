"""Course assignment: Lambda health and DynamoDB integration checks."""
import json
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def handler(event, context):
    if event.get("action") == "model_access_check":
        import boto3
        globals()["boto3"] = boto3
        return check_models()
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path = event.get("rawPath", "/health")
    stage = event.get("requestContext", {}).get("stage", "")
    if stage and stage != "$default" and path.startswith("/" + stage + "/"):
        path = path[len(stage) + 1:]
    request_id = getattr(context, "aws_request_id", "local")
    status = 200
    body = {"status": "ok", "service": "aws-environment-app", "developer_tool": "Codex"}
    if method == "GET" and path == "/api/environment":
        try:
            import boto3
            globals()["boto3"] = boto3
            body = check_environment()
        except Exception:
            logger.exception("Environment check failed request_id=%s", request_id)
            status, body = 503, {"status": "error", "message": "Environment check failed", "request_id": request_id}
    elif method != "GET" or path not in ("/health", "/storage-check"):
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


"""Infrastructure smoke checks only. No document ingestion or chatbot logic."""
import json
import os


def check_environment():
    s3 = boto3.client("s3")
    locations = {}
    for key in ("WEB_BUCKET", "DATA_BUCKET"):
        locations[key.lower()] = {
            "name": os.environ[key],
            "region": s3.get_bucket_location(Bucket=os.environ[key])["LocationConstraint"] or "us-east-1",
            "status": "accessible",
        }
    client = boto3.client("s3vectors")
    index = client.get_index(indexArn=os.environ["VECTOR_INDEX_ARN"])["index"]
    vectors = client.list_vectors(indexArn=os.environ["VECTOR_INDEX_ARN"], maxResults=1)
    return {
        "status": "ok", "scope": "development-environment-only",
        "storage": locations,
        "vector_index": {"name": index["indexName"], "dimension": index["dimension"],
                         "distance_metric": index["distanceMetric"], "empty": not bool(vectors.get("vectors"))},
        "embedding_model": os.environ["EMBEDDING_MODEL"],
        "generation_model": os.environ["GENERATION_MODEL"],
        "document_ingestion": "not_implemented", "chatbot": "not_implemented",
    }


def check_models():
    client = boto3.client("bedrock-runtime")
    result = client.invoke_model(modelId=os.environ["EMBEDDING_MODEL"],
        body=json.dumps({"inputText": "Development environment connectivity test", "dimensions": 256, "normalize": True}))
    embedding = json.loads(result["body"].read())["embedding"]
    result = client.converse(modelId=os.environ["GENERATION_MODEL"],
        messages=[{"role": "user", "content": [{"text": "Return only OK."}]}],
        inferenceConfig={"maxTokens": 8, "temperature": 0})
    return {"status": "ok", "embedding_dimensions": len(embedding),
            "generation_response": result["output"]["message"]["content"],
            "usage": result.get("usage", {})}
