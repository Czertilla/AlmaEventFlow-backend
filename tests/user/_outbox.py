from typing import Any


class Outbox:
    def __init__(self) -> None:
        self.verify: list[tuple[str, str]] = []
        self.reset: list[tuple[str, str]] = []
        self.events: list[tuple[str, tuple[Any, ...]]] = []
        self.notifications: list[Any] = []

    def last(self, name: str) -> tuple[Any, ...]:
        return [args for event, args in self.events if event == name][-1]

    def count(self, name: str) -> int:
        return sum(1 for event, _ in self.events if event == name)
