from src.app.exceptions import ConflictException


class EventCategoryIsNotALeafException(ConflictException):
    def __init__(self, obj_id: int):
        super().__init__(f"Event category with id {obj_id} is not a leaf.")
        self.extra = {
            "id": obj_id,
        }


class EventCategoryHasEventsException(ConflictException):
    def __init__(self, obj_id: int):
        super().__init__(f"Event category with id {obj_id} is a leaf.")
        self.extra = {
            "id": obj_id,
        }
