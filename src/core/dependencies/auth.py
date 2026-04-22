from typing import Annotated, Optional

from fastapi import Depends

from core.schema.user import UserJWT
from core.utils.jwt import create_jwt_auth, create_optional_jwt_auth


UserJWTDep = Annotated[UserJWT, Depends(create_jwt_auth())]
SuperUserJWTDep = Annotated[UserJWT, Depends(create_jwt_auth(superuser=True))]
ActiveUserJWTDep = Annotated[UserJWT, Depends(create_jwt_auth(verified=False))]

OptionalUserJWTDep = Annotated[
    Optional[UserJWT], Depends(create_optional_jwt_auth())
]
