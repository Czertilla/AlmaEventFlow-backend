from fastapi import FastAPI
from event.api import include_routers as include_event
from geo.api import include_routers as include_geo
from mail.api.kafka import include_routers as include_mail
from org.api import include_routers as include_org
from profile.api import include_routers as include_profile

# from report.api import include_routers as include_report
from user.api import include_routers as include_user


def include_routers(app: FastAPI):
    include_event(app)
    include_geo(app)
    include_mail(app)
    include_org(app)
    include_profile(app)
    include_user(app)
