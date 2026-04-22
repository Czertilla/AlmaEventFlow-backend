alembic -n event upgrade head

gunicorn event.main:app --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind=0.0.0.0:8000 --log-config=core/loggers/config.ini
