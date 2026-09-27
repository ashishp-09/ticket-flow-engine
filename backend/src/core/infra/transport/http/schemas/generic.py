from pydantic import BaseModel, ConfigDict


class GenericResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class GenericRequestSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GenericIdResponseSchema(BaseModel):
    id: int


class GenericResultRequestSchema(BaseModel):
    result: bool
