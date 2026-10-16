def compose_locality(city: str, region: str, country: str) -> str:
    parts: list[str] = []
    for part in (city, region, country):
        part = part.strip()
        if part and part not in parts:
            parts.append(part)
    return ", ".join(parts)
