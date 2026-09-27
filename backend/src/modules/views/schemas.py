from src.core.infra.transport.http import GenericRequestSchema


class RegisterViewsRequestSchema(GenericRequestSchema):
    object_ids: list[int]
