import re

SCHEMA_PACKAGES = {
    "core_v1": "core.schema.v1",
    "event_v1": "event.api.v1.schema",
    "event_v2": "event.api.v2.schema",
    "geo_v1": "geo.api.v1.schema",
    "geo_v2": "geo.api.v2.schema",
    "notify_v1": "notify.api.v1.schema",
    "org_v1": "org.api.v1.schema",
    "profile_v1": "profile.api.v1.schema",
    "profile_v2": "profile.api.v2.schema",
    "user_v1": "user.api.v1.schema",
    "user_v2": "user.api.v2.schema",
}

RESPONSES: dict[str, tuple[str, dict[str, str]]] = {
    "event_v1": (
        "event.api.v1.schema",
        {
            "attendance.AttendanceRead": "event.dto.attendance:AttendanceDTO",
            "collective.EventCollectiveRead": "event.dto.collective:CollectiveDTO",
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
            "attendance.AttendanceChanged": (
                "event.dto.attendance_change:AttendanceChangedDTO"
            ),
            "attendance.AttendanceReadV2": "event.dto.attendance:AttendanceViewDTO",
            "attendance.ParticipationCounts": (
                "event.dto.attendance_change:ParticipationCountsDTO"
            ),
            "calendar.AvailableFeeds": "event.dto.calendar:AvailableFeedsDTO",
            "calendar.FeedDescriptor": "event.dto.calendar:FeedDescriptorDTO",
            "calendar.SubscriptionRead": ("event.dto.calendar:CalendarSubscriptionDTO"),
            "collective_profile.CollectiveAttendanceSummary": (
                "event.dto.collective_profile:CollectiveAttendanceSummaryDTO"
            ),
            "collective_profile.CollectiveDay": (
                "event.dto.collective_profile:CollectiveDayDTO"
            ),
            "collective_profile.CollectiveEventItem": (
                "event.dto.collective_profile:CollectiveEventItemDTO"
            ),
            "collective_profile.CollectiveInfo": (
                "event.dto.collective_profile:CollectiveInfoDTO"
            ),
            "collective_profile.CollectiveMemberItem": (
                "event.dto.collective_profile:CollectiveMemberItemDTO"
            ),
            "collective_profile.CollectiveProfileRead": (
                "event.dto.collective_profile:CollectiveProfileDTO"
            ),
            "event_page.EventPageRead": "event.dto.event_page:EventPageDTO",
            "event_page.PageAttendance": "event.dto.event_page:PageAttendanceDTO",
            "event_page.PageEvent": "event.dto.event_page:PageEventDTO",
            "event_page.PageParticipation": (
                "event.dto.event_page:PageParticipationDTO"
            ),
            "event_page.RosterMember": "event.dto.feed:RosterMemberDTO",
            "feed.EventCard": "event.dto.feed:EventCardDTO",
            "feed.EventCardParticipation": "event.dto.feed:CardParticipationDTO",
            "feed.EventFeed": "event.dto.feed:FeedDTO",
            "feed.EventPlace": "event.dto.feed:PlaceDTO",
            "feed.ViewerCollective": "event.dto.feed:ViewerCollectiveDTO",
            "feed.ViewerContext": "event.dto.feed:ViewerContextDTO",
            "location.RecentLocationRead": "event.dto.location:RecentLocationDTO",
            "matrix.AttendanceMatrix": "event.dto.matrix:MatrixDTO",
            "matrix.CollectiveEvent": "event.dto.matrix:CollectiveEventDTO",
            "matrix.CollectiveEvents": "event.dto.matrix:CollectiveEventsDTO",
            "matrix.CollectiveRoster": "event.dto.matrix:RosterDTO",
            "member_profile.AttendanceByMonth": (
                "event.dto.member_profile:AttendanceByMonthDTO"
            ),
            "member_profile.AttendanceByType": (
                "event.dto.member_profile:AttendanceByTypeDTO"
            ),
            "member_profile.MemberAttendanceItem": (
                "event.dto.member_profile:MemberAttendanceItemDTO"
            ),
            "member_profile.MemberAttendanceSummary": (
                "event.dto.member_profile:MemberAttendanceSummaryDTO"
            ),
            "member_profile.MemberPerson": "event.dto.member_profile:MemberPersonDTO",
            "member_profile.MemberProfileRead": (
                "event.dto.member_profile:MemberProfileDTO"
            ),
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
    "geo_v2": (
        "geo.api.v2.schema",
        {
            "address.AddressReadV2": "geo.dto.address:AddressDTO",
            "location.LocationReadV2": "geo.dto.location:LocationDTO",
            "map.MapResponse": "geo.dto.map:MapViewDTO",
            "search.ExternalStatus": "geo.dto.search:ExternalStatusDTO",
            "search.SearchResponse": "geo.dto.search:SearchResultDTO",
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
    "profile_v2": (
        "profile.api.v2.schema",
        {
            "account_history.AccountLinkChangeRead": (
                "profile.dto.account_history:AccountLinkChangeDTO"
            ),
            "invite.InviteTokenRead": "profile.dto.invite:InviteTokenDTO",
            "profile.MyProfileRead": "profile.dto.my_profile:MyProfileDTO",
            "profile.MyStudentRead": "profile.dto.my_profile:MyStudentReadDTO",
            "reference.OrganizationRefRead": (
                "profile.dto.reference:OrganizationRefDTO"
            ),
        },
    ),
    "user_v1": (
        "user.api.v1.schema",
        {
            "session.SessionRead": "user.dto.session:SessionDTO",
            "telegram.TelegramLinkTokenRead": (
                "user.dto.telegram:TelegramLinkTokenDTO"
            ),
            "user.UserRead": "user.dto.user:UserDTO",
        },
    ),
    "user_v2": (
        "user.api.v2.schema",
        {
            "settings.UserSettingsRead": "user.dto.settings:UserSettingsDTO",
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
