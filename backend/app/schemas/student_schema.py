from pydantic import BaseModel, ConfigDict


class StudentSimple(BaseModel):
    id: int
    full_name: str

    model_config = ConfigDict(from_attributes=True)
