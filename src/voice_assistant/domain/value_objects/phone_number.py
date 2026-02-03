from pydantic import BaseModel, validator
from typing import Optional
import re


class PhoneNumber(BaseModel):
    """Value object representing a phone number"""
    number: str

    @validator('number')
    def validate_phone_number(cls, v):
        # Remove all non-digit characters for validation
        digits_only = re.sub(r'\D', '', v)
        
        # Basic validation: 10-15 digits
        if len(digits_only) < 10 or len(digits_only) > 15:
            raise ValueError('Phone number must contain 10-15 digits')
        
        # Ensure it starts with + or has country code
        if not v.startswith('+') and not v.startswith('0'):
            # Assume international format with +
            v = '+' + v
        
        return v

    def __str__(self) -> str:
        return self.number

    def __eq__(self, other) -> bool:
        if not isinstance(other, PhoneNumber):
            return False
        return self.number.replace('+', '') == other.number.replace('+', '')

    def normalize(self) -> str:
        """Return normalized phone number with only digits"""
        return re.sub(r'\D', '', self.number)