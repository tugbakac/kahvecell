import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PhoneNumberRequest(StrictRequest):
    phone_number: str = Field(
        description="GSM numarası; ör. +905551234567 veya 05551234567"
    )

    @field_validator("phone_number")
    @classmethod
    def normalize_phone_number(cls, value: str) -> str:
        phone_number = re.sub(r"[\s()-]", "", value)
        if phone_number.startswith("00"):
            phone_number = f"+{phone_number[2:]}"
        elif phone_number.startswith("0") and len(phone_number) == 11:
            phone_number = f"+90{phone_number[1:]}"
        elif phone_number.startswith("5") and len(phone_number) == 10:
            phone_number = f"+90{phone_number}"
        elif not phone_number.startswith("+"):
            raise ValueError("GSM numarasini uluslararasi formatta girin.")

        if not re.fullmatch(r"\+[1-9]\d{9,14}", phone_number):
            raise ValueError("GSM numarasi gecersiz.")
        return phone_number


class RegisterRequest(PhoneNumberRequest):
    full_name: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("full_name")
    @classmethod
    def strip_full_name(cls, value: str | None) -> str | None:
        return _validated_full_name(value)


class VerifyOTPRequest(PhoneNumberRequest):
    otp: str = Field(pattern=r"^\d{4}$")
    full_name: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("full_name")
    @classmethod
    def strip_full_name(cls, value: str | None) -> str | None:
        return _validated_full_name(value)


class RefreshRequest(StrictRequest):
    refresh_token: str = Field(min_length=1)


class ProfileUpdateRequest(StrictRequest):
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    preferences: dict[str, Any] | None = None

    @field_validator("full_name")
    @classmethod
    def strip_full_name(cls, value: str | None) -> str | None:
        return _validated_full_name(value)


def _validated_full_name(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        raise ValueError("Ad soyad bos olamaz.")
    return value
