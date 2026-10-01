import boto3

s3 = boto3.client(
    "s3",
    endpoint_url="http://localhost:4566",
    aws_access_key_id="test",
    aws_secret_access_key="test",
    region_name="us-east-1",
)

BUCKET = "safesite-datalake"

s3.create_bucket(Bucket=BUCKET)
print(f"Created bucket: {BUCKET}")

s3.put_object(Bucket=BUCKET, Key="test/hello.txt", Body=b"hello from safesite-ai")
print("Uploaded test object")

response = s3.get_object(Bucket=BUCKET, Key="test/hello.txt")
content = response["Body"].read().decode("utf-8")
print(f"Downloaded content: {content}")

buckets = s3.list_buckets()
print("Buckets:", [b["Name"] for b in buckets["Buckets"]])
