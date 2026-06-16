#!/bin/bash

alembic -n user upgrade head
alembic -n event upgrade head
alembic -n geo upgrade head
alembic -n org upgrade head
alembic -n profile upgrade head

gunicorn aef.main:app --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind=0.0.0.0:8000 --log-config=core/config/logger/config.ini --forwarded-allow-ips="*"
