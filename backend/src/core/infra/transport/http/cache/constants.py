from enum import StrEnum


class CacheTag(StrEnum):
    ADMIN_EVENT_CATEGORIES = "admin_event_categories"
    EVENT_CATEGORIES = "event_categories"
    CATEGORIES_BY_EVENT_ID = "category_by_event_id"
    UPCOMING_EVENTS = "upcoming_events"
