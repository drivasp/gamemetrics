from pydantic import BaseModel


class WishlistItemDTO(BaseModel):
    id: str
    game_slug: str
    game_name: str
    game_image: str | None = None
    game_price: float
    added_at: str | None = None


class AddWishlistDTO(BaseModel):
    game_slug: str
    game_name: str
    game_image: str | None = None
    game_price: float
