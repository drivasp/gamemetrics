from pydantic import BaseModel, Field


class CheckoutRequestDTO(BaseModel):
    coupon_code: str | None = None
    payment_method: str = Field(default="auto")  # auto | wallet | stripe | sandbox


class CheckoutResponseDTO(BaseModel):
    order_id: str
    payment_id: str
    status: str
    total: float
    currency: str = "USD"
    message: str
    purchases_count: int = 0
    checkout_url: str | None = None
    coupon_code: str | None = None
    coupon_discount: float = 0.0
    payment_method: str | None = None
    wallet_balance: float | None = None
