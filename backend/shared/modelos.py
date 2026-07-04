from pydantic import BaseModel


class VideoGameDTO(BaseModel):
    id: str
    slug: str
    name: str
    released: str
    rating: float
    metacritic: float
    genres: str
    platforms: str
    developers: str
    publishers: str
    esrbRating: str


class CountDTO(BaseModel):
    label: str
    count: int


class DimRecordDTO(BaseModel):
    dimId: int
    nombre: str
    codigo: str | None = None
    edadMinima: int | None = None
