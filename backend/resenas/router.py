import time
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException

from resenas.modelos_reviews import (
    ReviewDTO, ReviewPageDTO, CreateReviewDTO, UpdateReviewDTO,
    VoteReviewDTO, VoteResponseDTO,
)
from shared.auth_deps import require_token, esc
from shared.cliente_pinot import pinot_query
from shared.kafka_producer import kafka_send
from shared.pinot_utils import to_bool, to_ms

router = APIRouter(prefix="/reviews", tags=["reviews"])


async def _owns_game(user_id: str, game_slug: str) -> bool:
    rows = await pinot_query(
        f"SELECT purchase_id FROM fact_purchases "
        f"WHERE user_id = '{esc(user_id)}' AND game_slug = '{esc(game_slug)}' "
        f"AND deleted = false AND refunded = false LIMIT 1"
    )
    return len(rows) > 0


async def _product_matches_slug(product_id: str, game_slug: str) -> bool:
    rows = await pinot_query(
        f"SELECT product_id FROM fact_game_products "
        f"WHERE product_id = '{esc(product_id)}' AND slug = '{esc(game_slug)}' LIMIT 1"
    )
    if rows:
        return True
    rows = await pinot_query(
        f"SELECT id FROM fact_videogames "
        f"WHERE id = '{esc(product_id)}' AND slug = '{esc(game_slug)}' LIMIT 1"
    )
    return len(rows) > 0


async def _vote_counts(review_id: str) -> tuple[int, int]:
    rows = await pinot_query(
        f"SELECT helpful FROM fact_review_votes "
        f"WHERE review_id = '{esc(review_id)}' AND deleted = false LIMIT 500"
    )
    helpful = sum(1 for r in rows if to_bool(r[0]))
    not_helpful = len(rows) - helpful
    return helpful, not_helpful


async def _my_vote(review_id: str, voter_id: str | None) -> bool | None:
    if not voter_id:
        return None
    rows = await pinot_query(
        f"SELECT helpful FROM fact_review_votes "
        f"WHERE vote_id = '{esc(f'{voter_id}_{review_id}')}' AND deleted = false LIMIT 1"
    )
    if not rows:
        return None
    return to_bool(rows[0][0])


@router.get("/{game_slug}", response_model=ReviewPageDTO)
async def list_reviews(
    game_slug: str,
    authorization: Annotated[str | None, Header()] = None,
):
    voter_id = None
    if authorization:
        try:
            _, voter_id = require_token(authorization)
        except Exception:
            voter_id = None

    safe = esc(game_slug)
    rows = await pinot_query(
        f"SELECT review_id, user_id, product_id, game_slug, rating, comment, "
        f"created_at, updated_at FROM fact_reviews "
        f"WHERE game_slug = '{safe}' AND deleted = false "
        f"ORDER BY created_at DESC LIMIT 100"
    )
    reviews = []
    for r in rows:
        hc, nhc = await _vote_counts(r[0])
        reviews.append(ReviewDTO(
            review_id=r[0], user_id=r[1], product_id=r[2], game_slug=r[3],
            rating=int(r[4]), comment=r[5] or "",
            created_at=str(r[6]), updated_at=str(r[7]) if r[7] else None,
            helpful_count=hc,
            not_helpful_count=nhc,
            my_vote=await _my_vote(r[0], voter_id),
        ))
    # Ordenar por más útiles (detalle Steam)
    reviews.sort(key=lambda x: (x.helpful_count, x.rating), reverse=True)
    agg = await pinot_query(
        f"SELECT AVG(rating), COUNT(*) FROM fact_reviews "
        f"WHERE game_slug = '{safe}' AND deleted = false"
    )
    avg = float(agg[0][0] or 0) if agg else 0.0
    total = int(agg[0][1] or 0) if agg else 0
    return ReviewPageDTO(reviews=reviews, avg_rating=round(avg, 2), total=total)


@router.post("/votes/{review_id}", response_model=VoteResponseDTO)
async def vote_review(
    review_id: str,
    body: VoteReviewDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, voter_id = require_token(authorization)
    exists = await pinot_query(
        f"SELECT review_id, user_id FROM fact_reviews "
        f"WHERE review_id = '{esc(review_id)}' AND deleted = false LIMIT 1"
    )
    if not exists:
        raise HTTPException(404, "Reseña no encontrada")
    if exists[0][1] == voter_id:
        raise HTTPException(400, "No puedes votar tu propia reseña")

    vote_id = f"{voter_id}_{review_id}"
    now_ms = int(time.time() * 1000)
    await kafka_send("fact_review_votes", vote_id, {
        "vote_id": vote_id,
        "review_id": review_id,
        "voter_id": voter_id,
        "helpful": body.helpful,
        "created_at": now_ms,
        "deleted": False,
    })
    hc, nhc = await _vote_counts(review_id)
    if body.helpful:
        hc = max(hc, 1)
    else:
        nhc = max(nhc, 1)
    return VoteResponseDTO(
        review_id=review_id,
        helpful_count=hc,
        not_helpful_count=nhc,
        my_vote=body.helpful,
    )


@router.post("/{game_slug}", response_model=ReviewDTO, status_code=201)
async def create_review(
    game_slug: str,
    body: CreateReviewDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    if not await _owns_game(user_id, game_slug):
        raise HTTPException(403, "Debes comprar el juego para poder reseñarlo")
    if not await _product_matches_slug(body.product_id, game_slug):
        raise HTTPException(400, "product_id no corresponde a este juego")

    rid = f"{user_id}_{body.product_id}"
    existing = await pinot_query(
        f"SELECT review_id FROM fact_reviews WHERE review_id = '{esc(rid)}' "
        f"AND deleted = false LIMIT 1"
    )
    if existing:
        raise HTTPException(409, "Ya tienes una reseña de este juego")

    now_ms = int(time.time() * 1000)
    await kafka_send("fact_reviews", rid, {
        "review_id": rid,
        "user_id": user_id,
        "product_id": body.product_id,
        "game_slug": game_slug,
        "rating": body.rating,
        "comment": body.comment,
        "created_at": now_ms,
        "updated_at": now_ms,
        "deleted": False,
    })
    return ReviewDTO(
        review_id=rid, user_id=user_id, product_id=body.product_id,
        game_slug=game_slug, rating=body.rating, comment=body.comment,
        created_at=str(now_ms), updated_at=str(now_ms),
    )


@router.put("/{game_slug}", response_model=ReviewDTO)
async def update_review(
    game_slug: str,
    body: UpdateReviewDTO,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    rows = await pinot_query(
        f"SELECT review_id, product_id, rating, comment, created_at FROM fact_reviews "
        f"WHERE user_id = '{esc(user_id)}' AND game_slug = '{esc(game_slug)}' "
        f"AND deleted = false LIMIT 1"
    )
    if not rows:
        raise HTTPException(404, "Reseña no encontrada")

    rid, product_id, rating, comment, created_at = rows[0]
    new_rating = body.rating if body.rating is not None else int(rating)
    new_comment = body.comment if body.comment is not None else (comment or "")
    now_ms = int(time.time() * 1000)

    await kafka_send("fact_reviews", rid, {
        "review_id": rid,
        "user_id": user_id,
        "product_id": product_id,
        "game_slug": game_slug,
        "rating": new_rating,
        "comment": new_comment,
        "created_at": to_ms(created_at),
        "updated_at": now_ms,
        "deleted": False,
    })
    return ReviewDTO(
        review_id=rid, user_id=user_id, product_id=product_id,
        game_slug=game_slug, rating=new_rating, comment=new_comment,
        created_at=str(to_ms(created_at)), updated_at=str(now_ms),
    )


@router.delete("/{game_slug}", status_code=204)
async def delete_review(
    game_slug: str,
    authorization: Annotated[str | None, Header()] = None,
):
    _, user_id = require_token(authorization)
    rows = await pinot_query(
        f"SELECT review_id, product_id, rating, comment, created_at FROM fact_reviews "
        f"WHERE user_id = '{esc(user_id)}' AND game_slug = '{esc(game_slug)}' "
        f"AND deleted = false LIMIT 1"
    )
    if not rows:
        raise HTTPException(404, "Reseña no encontrada")

    rid, product_id, rating, comment, created_at = rows[0]
    now_ms = int(time.time() * 1000)
    await kafka_send("fact_reviews", rid, {
        "review_id": rid,
        "user_id": user_id,
        "product_id": product_id,
        "game_slug": game_slug,
        "rating": int(rating),
        "comment": comment or "",
        "created_at": to_ms(created_at),
        "updated_at": now_ms,
        "deleted": True,
    })
