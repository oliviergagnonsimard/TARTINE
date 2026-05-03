import boto3
import os
from dotenv import load_dotenv

load_dotenv()

R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID")
R2_ACCESS_KEY  = os.environ.get("R2_ACCESS_KEY")
R2_SECRET_KEY  = os.environ.get("R2_SECRET_KEY")
R2_PUBLIC_URL = os.environ.get("R2_PUBLIC_URL")
R2_BUCKET      = "tartine-circulaires"

s3 = boto3.client(
    "s3",
    endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
    aws_access_key_id=R2_ACCESS_KEY,
    aws_secret_access_key=R2_SECRET_KEY,
    region_name="auto"
)

def uploadImage(localPath, r2Path):
    s3.upload_file(localPath, R2_BUCKET, r2Path)

def imageExists(r2Path):
    try:
        s3.head_object(Bucket=R2_BUCKET, Key=r2Path)
        return True
    except:
        return False

def getImageUrl(r2Path):
    return f"{R2_PUBLIC_URL}/{r2Path}"