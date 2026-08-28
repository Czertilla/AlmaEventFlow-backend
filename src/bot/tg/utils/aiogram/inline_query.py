def parse_offset(offset: str | None) -> int:
    if not offset:
        return 0
    try:
        v = int(offset)
        return v if v >= 0 else 0
    except ValueError:
        return 0
