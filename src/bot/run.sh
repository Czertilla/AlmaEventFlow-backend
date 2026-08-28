alembic -n bot upgrade head

gunicorn bot.main:app --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind=0.0.0.0:8000 --log-config=core/config/logger/config.ini
