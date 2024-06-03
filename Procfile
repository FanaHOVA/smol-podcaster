web: flask --app web.py --debug run -p 3000
worker: celery -A tasks worker --loglevel=INFO -E -n smol_podcaster@%h