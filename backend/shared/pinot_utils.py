import time


def to_ms(v) -> int:
    if v is None:
        return int(time.time() * 1000)
    return int(float(v))


def to_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    return str(v).lower() in ("true", "1", "t", "yes")
