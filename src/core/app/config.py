from pydantic import BaseModel, Field, ConfigDict
from core.app.contextmanager import AppContextManager
from core.config.settings import settings
from core.utils.get_version import get_version


class AppConfig(BaseModel):
    """
    Application config class, inheriting from `Settings` and `SingletonMixin`.

    This class provides application-specific settings, including the application
     name and presets for the FastAPI application. It ensures that only one
     instance of the settings object is created due to the `SingletonMixin`.

    Attributes:
        app_name (str): The name of the application, retrieved from global
            settings.
        app_presets (dict): A dictionary containing presets for the FastAPI
            application, including the title and lifespan context manager.
    """

    title: str = settings.APP_NAME
    version: str = Field(default_factory=get_version)
    lifespan: AppContextManager = Field(default_factory=AppContextManager)

    model_config = ConfigDict(arbitrary_types_allowed=True)
