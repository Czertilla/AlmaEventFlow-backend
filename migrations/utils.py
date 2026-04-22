from typing import Iterable, Sequence

from alembic import op


def set_enum_values(
    enum_name: str,
    new_values: Iterable[str],
    references: Iterable[Sequence[str]],
):
    """
    Set new values for enum.

    Args:
        enum_name(str): System name of enum
        new_values(Iterable[str]): New values of enum
        references(Iterable[Sequence[str]]): References of enum in models

    Examples:
    ```python
        set_enum_values('promo_type_enum', (
            'BEST_OFFER',
            'NEW_PRODUCT',
            'NO_PROMOTION',
        ), [('advertisement_sale_package', 'promo_type')])
    ```
    """
    query_str = f"""
            ALTER TYPE {enum_name} RENAME TO {enum_name}_old;
            CREATE TYPE {enum_name} AS ENUM({", ".join(f"'{value}'" for value in new_values)});
            """
    for table_name, column_name in references:
        query_str += f"""
            ALTER TABLE {table_name} ALTER {column_name} DROP DEFAULT;
            ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE {enum_name} USING {column_name}::text::{enum_name};
        """
    query_str += f"""DROP TYPE {enum_name}_old;"""
    for q in query_str.split(";")[:-1]:
        op.execute(q)
