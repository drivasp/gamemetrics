from pydantic import BaseModel, Field


class ReviewDTO(BaseModel):
    review_id: str
    user_id: str
    product_id: str
    game_slug: str
    rating: int
    comment: str
    created_at: str
    updated_at: str | None = None
    helpful_count: int = 0
    not_helpful_count: int = 0
    my_vote: bool | None = None


class ReviewPageDTO(BaseModel):
    reviews: list[ReviewDTO]
    avg_rating: float
    total: int


class CreateReviewDTO(BaseModel):
    product_id: str
    rating: int = Field(ge=1, le=5)
    comment: str = Field(max_length=2000)


class UpdateReviewDTO(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=2000)


class VoteReviewDTO(BaseModel):
    helpful: bool


class VoteResponseDTO(BaseModel):
    review_id: str
    helpful_count: int
    not_helpful_count: int
    my_vote: bool
