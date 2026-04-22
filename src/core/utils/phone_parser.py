from re import sub

from core.utils.regions import REGIONS


def get_code_pattern(code) -> str | None:
    return f"+{code}"


def _parse_phone_number(number: str, code: str, length: int | None = None):
    code_pattern = get_code_pattern(code)
    if number.startswith(code_pattern) and (
        length is None or len(n := number.replace(code_pattern, "")) == length
    ):
        return int(n)
    return None


def parse_phone_number(
    number: str, code: str | None = None, length: int | None = None
) -> tuple[str, int] | None:
    number = sub(r"[^\d\+]", "", number)
    if number.startswith("8"):
        return ("ru", int(number[1:]))
    if number.startswith("+"):
        for k, v in REGIONS.items():
            result = _parse_phone_number(number, v["code"], v["length"])
            if result is not None:
                return (k, result)
        else:
            result = _parse_phone_number(number, code, length)
            if result is not None:
                return (k, result)
    return ("ru", int(number))
