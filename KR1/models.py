from pydantic import BaseModel

class User(BaseModel):
    name: str
    id: int

class Feedback(BaseModel):
    name: str
    message: str