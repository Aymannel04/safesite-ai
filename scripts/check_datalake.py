import boto3

s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:4566",
    aws_access_key_id="test",
    aws_secret_access_key="test",
    region_name="us-east-1",
)

response = s3.list_objects_v2(Bucket="safesite-datalake")
for obj in response.get("Contents", []):
    print(obj["Key"], obj["Size"], "bytes")
