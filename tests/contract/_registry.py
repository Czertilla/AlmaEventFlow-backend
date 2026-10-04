import re

SCHEMA_PACKAGES = {
    "core_v1": "core.schema.v1",
    "event_v1": "event.api.v1.schema",
    "event_v2": "event.api.v2.schema",
    "geo_v1": "geo.api.v1.schema",
    "notify_v1": "notify.api.v1.schema",
    "org_v1": "org.api.v1.schema",
    "profile_v1": "profile.api.v1.schema",
    "user_v1": "user.api.v1.schema",
}

RESPONSES: dict[str, tuple[str, dict[str, str]]] = {
    "event_v1": (
        "event.api.v1.schema",
        {
            "attendance.AttendanceRead": "event.dto.attendance:AttendanceDTO",
            "collective.MyCollectiveRead": (
                "event.dto.collective:CollectiveSummaryDTO"
            ),
            "event.EventRead": "event.dto.event:EventDTO",
            "link.LinkRead": "event.dto.link:LinkDTO",
            "me.MeEventRead": "event.dto.me:MeEventDTO",
            "member.MemberRead": "event.dto.member:MemberDTO",
            "participation.ParticipationRead": (
                "event.dto.participation:ParticipationDTO"
            ),
            "reward.RewardRead": "event.dto.reward:RewardDTO",
            "role.RolePreview": "event.dto.role:RolePreviewDTO",
            "role.RoleRead": "event.dto.role:RoleDTO",
            "stage.StageRead": "event.dto.stage:StageDTO",
        },
    ),
    "event_v2": (
        "event.api.v2.schema",
        {
            "calendar.AvailableFeeds": "event.dto.calendar:AvailableFeedsDTO",
            "calendar.FeedDescriptor": "event.dto.calendar:FeedDescriptorDTO",
            "calendar.SubscriptionRead": ("event.dto.calendar:CalendarSubscriptionDTO"),
        },
    ),
    "geo_v1": (
        "geo.api.v1.schema",
        {
            "address.AddressRead": "geo.dto.address:AddressDTO",
            "city.CityRead": "geo.dto.city:CityDTO",
            "location.LocationRead": "geo.dto.location:LocationDTO",
            "map.MapResult": "geo.dto.map:MapResultDTO",
            "point.Point": "geo.dto.point:PointDTO",
        },
    ),
    "notify_v1": (
        "notify.api.v1.schema",
        {
            "client.ClientRead": "notify.dto.client:ClientDTO",
            "preference.PreferenceItem": "notify.dto.preference:PreferenceItemDTO",
            "preference.PreferencesRead": "notify.dto.preference:PreferencesDTO",
        },
    ),
    "org_v1": (
        "org.api.v1.schema",
        {
            "collective.CollectiveRead": "org.dto.collective:CollectiveDTO",
            "faculty.FacultyRead": "org.dto.faculty:FacultyDTO",
            "organization.OrganizationRead": "org.dto.organization:OrganizationDTO",
            "university.UniversityRead": "org.dto.university:UniversityDTO",
        },
    ),
    "profile_v1": (
        "profile.api.v1.schema",
        {
            "contact.ContactItemRead": "profile.dto.contact:ContactDTO",
            "contact.ContactRead": "profile.dto.contact:ContactDTO",
            "diet.DietRead": "profile.dto.diet:DietDTO",
            "organization.OrganizationRead": (
                "profile.dto.organization:OrganizationDTO"
            ),
            "passport.NameVariantRead": "profile.dto.passport:NameVariantDTO",
            "passport.PassportItemRead": "profile.dto.passport:PassportDTO",
            "passport.PassportRead": "profile.dto.passport:PassportDTO",
            "person.PersonItemRead": "profile.dto.person:PersonDTO",
            "person.PersonRead": "profile.dto.person:PersonDTO",
            "profile.ProfileRead": "profile.dto.profile:ProfileDTO",
            "student.StudentDegreeRead": "profile.dto.student:StudentDegreeDTO",
            "student.StudentGroupRead": "profile.dto.student:StudentGroupDTO",
            "student.StudentRead": "profile.dto.student:StudentDTO",
        },
    ),
    "user_v1": (
        "user.api.v1.schema",
        {
            "invite.InviteTokenRead": "user.dto.invite:InviteTokenDTO",
            "session.SessionRead": "user.dto.session:SessionDTO",
            "telegram.TelegramLinkTokenRead": (
                "user.dto.telegram:TelegramLinkTokenDTO"
            ),
            "user.UserRead": "user.dto.user:UserDTO",
        },
    ),
}

BUILT_BY_ROUTER = {"event.api.v2.schema": {"calendar.SubscriptionCreated"}}

MIGRATED_LAYERS = {
    "event": ("service", "repository", "uow", "dto", "models"),
    "core": ("dto", "service", "uow", "database"),
    "org": ("service", "repository", "uow", "dto", "models"),
    "geo": ("service", "repository", "uow", "dto", "models"),
    "profile": ("service", "repository", "uow", "dto", "models"),
    "notify": ("service", "repository", "uow", "dto", "models"),
    "bot": ("service", "repository", "uow", "dto", "models"),
    "user": ("service", "repository", "repositories", "uow", "dto", "models"),
}

FORBIDDEN = {
    "event": (
        re.compile(r"^event\.api(\.|$)"),
        re.compile(r"^core\.schema\.v\d+"),
    ),
    "core": (re.compile(r"^core\.schema\.v\d+"),),
    "org": (
        re.compile(r"^org\.api\.v\d+"),
        re.compile(r"^core\.schema\.v\d+"),
    ),
    "geo": (
        re.compile(r"^geo\.api\.v\d+"),
        re.compile(r"^core\.schema\.v\d+"),
    ),
    "profile": (
        re.compile(r"^profile\.api\.v\d+"),
        re.compile(r"^core\.schema\.v\d+"),
    ),
    "notify": (
        re.compile(r"^notify\.api\.v\d+"),
        re.compile(r"^core\.schema\.v\d+"),
    ),
    "bot": (
        re.compile(r"^bot\.api\.v\d+"),
        re.compile(r"^core\.schema\.v\d+"),
    ),
    "user": (
        re.compile(r"^user\.api(\.|$)"),
        re.compile(r"^core\.schema\.v\d+"),
    ),
}
