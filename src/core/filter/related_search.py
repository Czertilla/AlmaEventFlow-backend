from typing import Any, ClassVar

from sqlalchemy import or_

from core.filter.ordered import OrderedFilter

type SearchPath = tuple[tuple[Any, ...], tuple[Any, ...]]


class RelatedSearchFilter(OrderedFilter):
    """``search`` also matches columns of related rows.

    ``search_relation``/``search_related`` name one related row; ``search_paths``
    lists any number of ``(relations, columns)`` pairs, where ``relations`` is a
    chain walked through ``has()`` (``(Attendance.member, Member.person)``).
    """

    search: str | None = None

    class Constants(OrderedFilter.Constants):
        search_relation: ClassVar[Any]
        search_related: ClassVar[tuple[Any, ...]] = ()
        search_paths: ClassVar[tuple[SearchPath, ...]] = ()

    @classmethod
    def _search_paths(cls) -> list[SearchPath]:
        paths = list(cls.Constants.search_paths)
        relation = getattr(cls.Constants, "search_relation", None)
        if relation is not None:
            paths.append(((relation,), cls.Constants.search_related))
        return paths

    def _search_clauses(self, term: str) -> list[Any]:
        pattern = f"%{term}%"
        clauses = super()._search_clauses(term)
        for relations, columns in self._search_paths():
            clause = or_(*[column.ilike(pattern) for column in columns])
            for relation in reversed(relations):
                clause = relation.has(clause)
            clauses.append(clause)
        return clauses
