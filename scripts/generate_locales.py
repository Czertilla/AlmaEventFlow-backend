#!/usr/bin/env python3
"""
Скрипт для генерации enum-классов локализации на основе YAML-файла.
"""

from pathlib import Path

import yaml


def _get_class_name(key: str) -> str:
    words = key.replace("_", " ").split()
    return "".join([word.capitalize() for word in words])


def _handle_value(key: str, value: str | dict, level=1):
    if key.startswith("_"):
        return []
    code = []
    if isinstance(value, dict):
        # Вложенный класс для сложных структур
        class_name = _get_class_name(key)
        code.append(f'{"\t" * level}@prefix("{key}.")')
        code.append(f"{'\t' * level}class {class_name}(Enum):")
        for k, v in value.items():
            code += _handle_value(k, v, level + 1)
    else:
        code.append(f'{"\t" * level}{key} = "{key}"')
        code.append(
            f'{"\t" * level}"""{value}"""'.replace("\n", "\n" + "\t" * level)
        )
    return code


def parse_yaml_to_enums(yaml_path: Path, output_path: Path) -> None:
    """
    Парсит YAML-файл и генерирует enum-классы для локализации.

    Args:
        yaml_path: Путь к YAML-файлу с локализацией.
        output_path: Путь к выходному файлу с enum-классами.
    """
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or "en" not in data:
        raise ValueError("YAML-файл не содержит данных или раздела 'en'")

    en_data: dict[str, dict | str] = data["en"]

    # Генерация кода для enum-классов
    code = [
        "from enum import Enum",
        "",
        "from core.utils.enum.prefix import prefix",
        "",
        "",
        "class Locale(Enum):",
        '    en = "en"',
        '    ru = "ru"',
        "",
        "",
        "class LocaleKey(Enum):",
    ]

    # Обработка корневых ключей
    for key, value in en_data.items():
        code += _handle_value(key, value)

    # Запись результата в файл
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(code))


if __name__ == "__main__":
    yaml_path = Path("res/locales/HTML.en.yml")
    output_path = Path("src/bot/enum/locales.py")
    parse_yaml_to_enums(yaml_path, output_path)
    print(f"Файл {output_path} успешно сгенерирован.")
