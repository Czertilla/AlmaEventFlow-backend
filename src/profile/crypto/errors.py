class KeyConfigError(Exception):
    """The key provider is configured wrongly; the service must not start."""


class KeyProviderError(Exception):
    """A key operation failed. The message never carries keys, context or payload."""

    code = "key_provider_error"


class KeyProviderUnavailableError(KeyProviderError):
    code = "provider_unavailable"


class KeyUnwrapError(KeyProviderError):
    code = "unwrap_failed"


class DecryptionError(Exception):
    """A stored value could not be decrypted; `code` says why, for the logs only."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code
