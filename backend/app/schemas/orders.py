from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class OrderCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shop_id: int = Field(gt=0)
    product_id: int = Field(gt=0)
    size: Literal["S", "M", "L"] = "M"
    sugar_level: int = Field(default=0, ge=0, le=5)
    milk_type: Literal["NONE", "WHOLE", "LACTOSE_FREE", "OAT", "ALMOND"] = "WHOLE"
    extra_shots: int = Field(default=0, ge=0, le=3)
    notes: str | None = Field(default=None, max_length=500)

    def customizations(self) -> dict[str, Any]:
        return {
            "size": self.size,
            "sugar_level": self.sugar_level,
            "milk_type": self.milk_type,
            "extra_shots": self.extra_shots,
            "notes": self.notes,
        }


class OrderStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ACCEPTED", "PREPARING", "READY"]


class QRCodePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order_id: str
    user_id: str
    shop_id: str
    created_at: str
    signature: str = Field(pattern=r"^[a-f0-9]{64}$")
