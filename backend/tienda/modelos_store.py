from pydantic import BaseModel

from shared.modelos import VideoGameDTO, CountDTO


class StoreGameDTO(BaseModel):
    id: str
    product_id: str
    slug: str
    name: str
    released: str
    rating: float
    metacritic: float
    genres: str
    platforms: str
    developers: str
    publishers: str
    esrb_rating: str
    price: float
    original_price: float | None = None
    discount_pct: float = 0.0
    is_free: bool
    background_image: str | None = None
    trailer_url: str | None = None


class StoreGameDetailDTO(StoreGameDTO):
    description: str | None = None
    screenshots: list[str] = []
    similar: list[StoreGameDTO] = []


class StorePageDTO(BaseModel):
    games: list[StoreGameDTO]
    total: int
    page: int
    size: int


class GameMediaDTO(BaseModel):
    background_image: str | None = None
    description: str | None = None
    screenshots: list[str] = []
    trailer_url: str | None = None
