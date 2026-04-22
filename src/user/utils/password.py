from fastapi_users.password import PasswordHelper as Base


class PasswordHelper(Base):
    def hash(self, password) -> bytes:
        return super().hash(password).encode()
