from profile.api import include_routers as include_profile

from fastapi import FastAPI

from bot.api import include_routers as include_bot
from event.api import include_routers as include_event
from geo.api import include_routers as include_geo
from mail.api.kafka import include_routers as include_mail
from notify.api import include_routers as include_notify
from org.api import include_routers as include_org

# from report.api import include_routers as include_report
from user.api import include_routers as include_user


def include_routers(app: FastAPI):
    include_event(app)
    include_geo(app)
    include_mail(app)
    include_notify(app)
    include_org(app)
    include_profile(app)
    include_bot(app)
    include_user(app)
