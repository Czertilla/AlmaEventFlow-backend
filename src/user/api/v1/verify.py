from typing import Type

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from fastapi_users import exceptions, models, schemas
from fastapi_users.manager import BaseUserManager, UserManagerDependency

templates = Jinja2Templates(directory="templates/user")


def get_verify_router(
    get_user_manager: UserManagerDependency[models.UP, models.ID],
    user_schema: Type[schemas.U],
):
    router = APIRouter(prefix="/v1")

    @router.get(
        "/verify/email",
        response_class=HTMLResponse,
        name="verify:verify",
    )
    async def verify(
        request: Request,
        token: str,
        user_manager: BaseUserManager[models.UP, models.ID] = Depends(
            get_user_manager
        ),
    ) -> HTMLResponse:
        try:
            await user_manager.verify(token, request)
            return templates.TemplateResponse(
                "verification_result.html",
                {
                    "request": request,
                    "success": True,
                    "login_url": "https://aef.czertilla.ru/auth/login",
                },
            )
        except exceptions.UserAlreadyVerified:
            return templates.TemplateResponse(
                "verification_result.html",
                {
                    "request": request,
                    "success": False,
                    "title": "Уже подтверждён",
                    "message": "Ваш аккаунт уже был подтверждён ранее.",
                },
            )
        except (exceptions.InvalidVerifyToken, exceptions.UserNotExists):
            return templates.TemplateResponse(
                "verification_result.html",
                {
                    "request": request,
                    "success": False,
                },
            )

    return router
