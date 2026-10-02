import re

SCHEMA_PACKAGES = {
    "core_v1": "core.schema.v1",
    "event_v1": "event.api.v1.schema",
    "event_v2": "event.api.v2.schema",
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
}

BUILT_BY_ROUTER = {"event.api.v2.schema": {"calendar.SubscriptionCreated"}}

MIGRATED_LAYERS = {
    "event": ("service", "repository", "uow", "dto", "models"),
    "core": ("dto", "service", "uow", "database"),
}

FORBIDDEN = {
    "event": (
        re.compile(r"^event\.api(\.|$)"),
        re.compile(r"^core\.schema\.v\d+"),
    ),
    "core": (re.compile(r"^core\.schema\.v\d+"),),
}
