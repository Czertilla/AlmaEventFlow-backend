from dataclasses import replace
from profile.enum.audience import Audience

from .field import Column, PersonalField, Reference, Source

PERSON_FULLNAME = "person.fullname"
UNIT_HEAD_TYPES = ("university", "faculty")

PRIVATE, CONTEXT, ALL_USERS = Audience.PRIVATE, Audience.CONTEXT, Audience.ALL_USERS


def _contact(kind: str, label: str, widest: Audience = ALL_USERS) -> PersonalField:
    return PersonalField(
        key=f"contact.{kind}",
        label=label,
        columns=(Column("contact", "value", where=("type", kind)),),
        audience_default=PRIVATE,
        audience_min=PRIVATE,
        audience_max=widest,
    )


def _sensitive(key: str, label: str, *columns: Column) -> PersonalField:
    return PersonalField(
        key=key,
        label=label,
        columns=columns,
        audience_default=PRIVATE,
        audience_min=PRIVATE,
        audience_max=PRIVATE,
    )


def _encrypted(key: str, label: str, *columns: Column) -> PersonalField:
    return replace(_sensitive(key, label, *columns), encrypted=True)


FIELDS: tuple[PersonalField, ...] = (
    PersonalField(
        key=PERSON_FULLNAME,
        label="ФИО",
        columns=(
            Column("person", "surname"),
            Column("person", "name"),
            Column("person", "patronymic"),
        ),
        audience_default=CONTEXT,
        audience_min=CONTEXT,
        audience_max=ALL_USERS,
        audience_default_for_unit_head=ALL_USERS,
    ),
    PersonalField(
        key="profile.birthdate",
        label="Дата рождения",
        columns=(Column("profile", "birthdate"),),
        audience_default=PRIVATE,
        audience_min=PRIVATE,
        audience_max=ALL_USERS,
    ),
    PersonalField(
        key="profile.workplace",
        label="Место работы",
        columns=(Column("profile", "workplace_id"),),
        audience_default=PRIVATE,
        audience_min=PRIVATE,
        audience_max=ALL_USERS,
        grantable=False,
    ),
    PersonalField(
        key="profile.diet",
        label="Диета",
        columns=(Column("profile", "diet_id", ref=Reference("diet")),),
        audience_default=PRIVATE,
        audience_min=PRIVATE,
        audience_max=CONTEXT,
    ),
    _contact("email", "Электронная почта"),
    _contact("phone", "Телефон"),
    _contact("tg", "Telegram"),
    _contact("vk", "ВКонтакте"),
    _contact("address", "Адрес", widest=CONTEXT),
    PersonalField(
        key="student.group",
        label="Учебная группа",
        columns=(Column("student", "group_id", ref=Reference("student_group")),),
        audience_default=CONTEXT,
        audience_min=PRIVATE,
        audience_max=ALL_USERS,
    ),
    _sensitive(
        "student.student_id",
        "Номер студенческого билета",
        Column("student", "student_id"),
    ),
    _sensitive(
        "student.study_terms",
        "Условия обучения",
        Column("student", "is_budget"),
        Column("student", "is_full"),
        Column("student", "is_active"),
    ),
    _encrypted("passport.number", "Номер паспорта", Column("passport", "number")),
    _encrypted(
        "passport.issued_authority",
        "Кем выдан паспорт",
        Column("passport", "issued_authority"),
    ),
    _encrypted(
        "passport.issued_date",
        "Дата выдачи паспорта",
        Column("passport", "issued_date", kind="date"),
    ),
    _encrypted(
        "passport.expire_date",
        "Срок действия паспорта",
        Column("passport", "expire_date", kind="date"),
    ),
    _sensitive(
        "name_variant.fullname",
        "Вариант ФИО из паспорта",
        Column("name_variant", "surname"),
        Column("name_variant", "name"),
        Column("name_variant", "patronymic"),
    ),
)

SOURCES: tuple[Source, ...] = (
    Source("person", person="id"),
    Source("profile", person="id"),
    Source("contact", person="person_id"),
    Source("student", person="id"),
    Source("passport", person="profile_id"),
    Source("name_variant", parent="passport"),
)

_BY_KEY = {field.key: field for field in FIELDS}
_SOURCES = {source.table: source for source in SOURCES}


class UnknownFieldError(KeyError): ...


def all_fields() -> tuple[PersonalField, ...]:
    return tuple(_BY_KEY.values())


def get_field(key: str) -> PersonalField:
    try:
        return _BY_KEY[key]
    except KeyError:
        raise UnknownFieldError(key) from None


def encrypted_columns(table: str) -> dict[str, Column]:
    return {
        column.column: column
        for field in _BY_KEY.values()
        if field.encrypted
        for column in field.columns
        if column.table == table
    }


def sensitive_fields_of(table: str) -> tuple[PersonalField, ...]:
    return tuple(
        field
        for field in _BY_KEY.values()
        if field.sensitive and any(column.table == table for column in field.columns)
    )


def grantable_fields() -> tuple[PersonalField, ...]:
    return tuple(
        field for field in _BY_KEY.values() if field.grantable and not field.deprecated
    )


def all_sources() -> tuple[Source, ...]:
    return tuple(_SOURCES.values())


def source_of(table: str) -> Source:
    return _SOURCES[table]
