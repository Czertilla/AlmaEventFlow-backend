from fastapi import HTTPException


class UsernameAlreadyExists(HTTPException):
    def __init__(self, *, detail="USERNAME_ALREADY_EXISTS", headers=None):
        super().__init__(400, detail, headers)
