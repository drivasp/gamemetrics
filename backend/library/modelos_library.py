from pydantic import BaseModel


class LibraryItemDTO(BaseModel):
    purchase_id: str
    product_id: str
    game_slug: str
    game_name: str
    game_image: str | None = None
    amount: float
    purchased_at: str
    refunded: bool = False
