from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class PostBase(BaseModel):
    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    category: str = Field(..., pattern="^(Temple|Priest|Sadhu)$")
    image_url: Optional[str] = None

class PostCreate(PostBase):
    pass

class Post(PostBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class PostUpdate(PostBase):
    pass

class PostOut(Post):
    pass

class UserBase(BaseModel):
    username: str = Field(..., min_length=1)

class UserCreate(UserBase):
    password: str = Field(..., min_length=1)

class User(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

class DonationBase(BaseModel):
    name: str = Field(..., min_length=1)
    email: str = Field(..., min_length=1)
    amount: int = Field(..., gt=0)
    message: Optional[str] = None

class DonationCreate(DonationBase):
    pass

class Donation(DonationBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True




