from pydantic import BaseModel, Field


class CartItemDTO(BaseModel):
    id: str
    product_id: str
    game_slug: str
    game_name: str
    game_image: str | None = None
    unit_price: float
    quantity: int = 1
    line_total: float


class CartDTO(BaseModel):
    items: list[CartItemDTO]
    subtotal: float
    discount_total: float = 0.0
    total: float
    item_count: int


class AddCartItemDTO(BaseModel):
    product_id: str
    game_slug: str
    game_name: str
    game_image: str | None = None
    unit_price: float = Field(ge=0)
    quantity: int = Field(default=1, ge=1, le=10)
