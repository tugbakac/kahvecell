import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

PlanType = Literal["STARTER", "PREMIUM", "UNLIMITED"]


class SubscriptionPaymentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_type: PlanType
    card_number: str = Field(
        description=(
            "Simulated card number. Use 4242-4242-4242-4242 for success "
            "or 4000-0000-0000-0002 for a decline."
        )
    )

    @field_validator("card_number")
    @classmethod
    def normalize_card_number(cls, value: str) -> str:
        card_number = re.sub(r"[\s-]", "", value)
        if not re.fullmatch(r"\d{16}", card_number):
            raise ValueError("Kart numarasi 16 rakamdan olusmalidir.")
        return card_number
