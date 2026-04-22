from math import ceil


def get_total_pages(total: int, limit: int) -> int:
    return ceil(total / limit)


def get_offset(page: int, limit: int) -> int:
    return page * limit
