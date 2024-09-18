web: gunicorn web:app
worker: celery -A tasks worker --loglevel=INFO -E -n smol_podcaster@%h