"""Infrastructure smoke checks only. No document ingestion or chatbot logic."""
import json
import os
import boto3


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
