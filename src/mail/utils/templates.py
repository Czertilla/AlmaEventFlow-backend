from functools import lru_cache

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATES_DIR = "templates/email"


@lru_cache
def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )


def render_template(template: str, context: dict[str, str]) -> str:
    """Renders ``templates/email/{template}.html`` with the given context."""
    tmpl = _env().get_template(f"{template}.html")
    return tmpl.render(**context)
