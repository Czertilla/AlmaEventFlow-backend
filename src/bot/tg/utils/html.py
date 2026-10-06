from html.parser import HTMLParser


def html_escape(text: str):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


class _TextOnly(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def plain_text(markup: str) -> str:
    """Drops Telegram HTML tags, for the places that only take plain text
    (a callback answer, for one)."""
    parser = _TextOnly()
    parser.feed(markup)
    parser.close()
    return "".join(parser.parts).strip()
