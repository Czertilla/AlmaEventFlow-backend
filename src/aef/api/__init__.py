from fastapi import APIRouter, FastAPI
from event.api import include_routers as include_event
from geo.api import include_routers as include_geo
from mail.api.kafka import include_routers as include_mail
from org.api import include_routers as include_org
from profile.api import include_routers as include_profile

# from report.api import include_routers as include_report
from user.api import include_routers as include_user

routers = [
    (event_router := APIRouter(prefix=(p := "/event")), p),
    (geo_router := APIRouter(prefix=(p := "/geo")), p),
    (mail_router := APIRouter(prefix=(p := "/mail")), p),
    (org_router := APIRouter(prefix=(p := "/org")), p),
    (profile_router := APIRouter(prefix=(p := "/profile")), p),
    (report_router := APIRouter(prefix=(p := "/report")), p),
    (user_router := APIRouter(prefix=(p := "/user")), p),
]


include_event(event_router)
include_geo(geo_router)
include_mail(mail_router)
include_org(org_router)
include_profile(profile_router)
# include_report(report_router)
include_user(user_router)


def include_routers(app: FastAPI):
    for router, prefix in routers:
        app.include_router(router, tags=[prefix])
