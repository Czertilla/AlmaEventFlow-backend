from .contact import ContactORM
from .diet import DietORM
from .organization import OrganizationORM
from .passport import PassportORM, NameVariantORM
from .person import PersonORM
from .profile import ProfileORM
from .student import StudentORM, StudentGroupORM, StudentDegree

__all__ = [
    "ContactORM",
    "DietORM",
    "OrganizationORM",
    "PassportORM",
    "NameVariantORM",
    "PersonORM",
    "ProfileORM",
    "StudentORM",
    "StudentGroupORM",
    "StudentDegree",
]