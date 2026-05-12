from pydantic import BaseModel, Field
from models.hub import Hub

class Connection(BaseModel):
    hub_1: Hub
    hub_2: Hub
    max_link_capacity: int = Field(ge=0)
