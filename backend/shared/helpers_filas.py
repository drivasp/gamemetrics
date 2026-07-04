from collections import defaultdict

from shared.cliente_pinot import pinot_query, TABLE
from shared.modelos import VideoGameDTO, CountDTO


def _str(row: list, i: int) -> str:
    v = row[i]
    return "" if v is None else str(v)


def _float(row: list, i: int) -> float:
    v = row[i]
    if v is None:
        return 0.0
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def _int(row: list, i: int) -> int:
    v = row[i]
    if v is None:
        return 0
    try:
        return int(float(str(v)))
    except (ValueError, TypeError):
        return 0


def map_game(row: list) -> VideoGameDTO:
    return VideoGameDTO(
        id=_str(row, 0),
        slug=_str(row, 1),
        name=_str(row, 2),
        released=_str(row, 3),
        rating=_float(row, 4),
        metacritic=_float(row, 5),
        genres=_str(row, 6),
        platforms=_str(row, 7),
        developers=_str(row, 8),
        publishers=_str(row, 9),
        esrbRating=_str(row, 10),
    )


async def count_by_split_field(field: str, semana: int) -> list[CountDTO]:
    sql = (
        f"SELECT {field}, COUNT(*) AS cnt "
        f"FROM {TABLE} "
        f"WHERE {field} != '' AND semana <= {semana} "
        f"GROUP BY {field} ORDER BY cnt DESC"
    )
    rows = await pinot_query(sql)
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        combo = _str(row, 0)
        cnt = _int(row, 1)
        if not combo.strip():
            continue
        for token in combo.split("||"):
            label = token.strip()
            if label:
                counts[label] += cnt
    return sorted(
        [CountDTO(label=k, count=v) for k, v in counts.items()],
        key=lambda x: x.count,
        reverse=True,
    )


async def count_table(table: str) -> int:
    rows = await pinot_query(f"SELECT COUNT(*) FROM {table}")
    return _int(rows[0], 0) if rows else 0
