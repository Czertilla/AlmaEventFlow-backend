from typing import Annotated

from fastapi import Depends

from core.config.settings import settings
from core.utils.s3_client import S3Client


def get_s3_client() -> S3Client:
    return S3Client(
        settings.S3_URL,
        settings.S3_BUCKET_NAME,
        settings.S3_ACCESS_KEY.get_secret_value(),
        settings.S3_SECRET_KEY.get_secret_value(),
    )


S3Dep = Annotated[S3Client, Depends(get_s3_client)]
