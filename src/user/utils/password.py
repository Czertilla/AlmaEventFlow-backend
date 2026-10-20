from typing import cast

from fastapi_users.password import PasswordHelper as Base


class PasswordHelper(Base):
    def hash(self, password: str | bytes) -> bytes:  # pyright: ignore[reportIncompatibleMethodOverride]
        return super().hash(cast("str", password)).encode()

    def verify_and_update(
        self, plain_password: str | bytes, hashed_password: str | bytes
    ) -> tuple[bool, str | None]:
        return super().verify_and_update(
            cast("str", plain_password), cast("str", hashed_password)
        )
