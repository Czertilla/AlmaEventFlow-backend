from aiohttp import ClientSession
from types import TracebackType
from typing import Self



class HTTPClient:
    """
    HTTP client wrapper for making requests to a specific base URL.

    Encapsulates an aiohttp ClientSession and a base URL for convenient request building.

    Attributes:
        session (ClientSession): The aiohttp ClientSession instance.
    """

    def __init__(self, session: ClientSession) -> None:
        """
        Initializes the HTTPClient with a base URL and ClientSession.

        Args:
            session (ClientSession): The aiohttp ClientSession instance.
        """
        self.session = session

    async def __aenter__(self) -> Self:
        self.session = await self.session.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None
    ):
        await self.session.__aexit__(exc_type, exc_val, exc_tb)