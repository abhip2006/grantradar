"""Contact form schemas."""
from pydantic import BaseModel, EmailStr, Field
from typing import Literal


class ContactFormRequest(BaseModel):
    """Contact form submission request."""
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    subject: Literal[
        'general',
        'support',
        'billing',
        'enterprise',
        'partnership',
        'feedback'
    ] = 'general'
    message: str = Field(..., min_length=10, max_length=5000)


class ContactFormResponse(BaseModel):
    """Contact form submission response."""
    success: bool
    message: str
