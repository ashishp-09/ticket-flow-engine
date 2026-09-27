class CacheError(Exception):
    pass


class CacheUnavailableError(CacheError):
    def __init__(self, message: str = "Cache storage is temporarily unavailable"):
        self.message = message
        super().__init__(self.message)
