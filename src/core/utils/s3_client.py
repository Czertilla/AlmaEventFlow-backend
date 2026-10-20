from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from logging import getLogger
from typing import Any

from aiobotocore.session import (
    get_session,  # pyright: ignore[reportUnknownVariableType]
)
from botocore.exceptions import ClientError

logger = getLogger(__name__)


class S3Client:
    def __init__(
        self,
        endpoint_url: str,
        bucket_name: str,
        access_key: str,
        secret_key: str,
    ):
        self.config = {
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "endpoint_url": endpoint_url,
        }
        self.bucket_name = bucket_name
        self.session: Any = get_session()

    @asynccontextmanager
    async def get_client(self) -> AsyncGenerator[Any]:
        async with self.session.create_client("s3", **self.config) as client:
            yield client

    async def put_file(self, file_name: str, data: bytes, **headers: Any):
        try:
            async with self.get_client() as client:
                await client.put_object(
                    Bucket=self.bucket_name, Key=file_name, Body=data, **headers
                )
                logger.debug(
                    f"File {file_name} uploaded to {self.bucket_name} "
                    f"({len(data) / 1024**2:.4} MB)"
                )
        except ClientError as e:
            logger.error("Error uploading file: %s", e)
            raise e

    async def delete_file(self, file_name: str):
        try:
            async with self.get_client() as client:
                await client.delete_object(
                    Bucket=self.bucket_name, Key=file_name
                )
                logger.debug(
                    "File %s deleted from %s", file_name, self.bucket_name
                )
        except ClientError as e:
            logger.error("Error deleting file: %s", e)
            raise e

    async def get_file(self, file_name: str) -> bytes:
        try:
            async with self.get_client() as client:
                response: dict[str, Any] = await client.get_object(
                    Bucket=self.bucket_name, Key=file_name
                )
                logger.debug(
                    "File %s downloaded from %s", file_name, self.bucket_name
                )
                body = response.get("Body")
                assert body is not None
                return await body.read()
        except ClientError as e:
            logger.error("Error downloading file: %s", e)
            raise e

    async def get_file_meta(self, file_name: str) -> dict[str, Any]:
        try:
            async with self.get_client() as client:
                response: dict[str, Any] = await client.get_object_acl(
                    Bucket=self.bucket_name, Key=file_name
                )
                logger.debug(
                    "File %s got meta from %s", file_name, self.bucket_name
                )
                return response
        except ClientError as e:
            logger.error("Error getting meta of file: %s", e)
            raise e

    async def get_presigned_url(
        self, file_name: str, expires_in: int = 3600
    ) -> str:
        try:
            async with self.get_client() as client:
                url = await client.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={
                        "Bucket": self.bucket_name,
                        "Key": file_name,
                    },
                    ExpiresIn=expires_in,
                    HttpMethod="GET",
                )
                return url
        except ClientError as e:
            logger.error("Error getting file url: %s", e)
            raise e
