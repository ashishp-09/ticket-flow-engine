from src.app.exceptions import ConflictException


class NoTicketsAvailableException(ConflictException):
    def __init__(self, obj_id: int, available: int, requested: int | None = None):
        message = (f"Not enough tickets available in category with id '{obj_id}' to process an order."
                   f" Available: {available}.")
        if requested is not None:
            message += f" Requested: {requested}."

        super().__init__(message)
        self.extra = {
            "category_id": obj_id,
            "available": available,
            "requested": requested
        }
