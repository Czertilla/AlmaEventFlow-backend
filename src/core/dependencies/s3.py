from typing import Annotated
from fastapi import Depends
from core.config.settings import settings
from core.utils.s3_client import S3Client


def get_s3_client(
    endpoint_url: str = settings.S3_URL,
    bucket_name: str = settings.S3_BUCKET_NAME,
    access_key: str = settings.S3_ACCESS_KEY.get_secret_value(),
    secret_key: str = settings.S3_SECRET_KEY.get_secret_value(),
):
    return S3Client(endpoint_url, bucket_name, access_key, secret_key)


S3Dep = Annotated[S3Client, Depends(get_s3_client)]