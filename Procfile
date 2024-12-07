web: waitress-serve --listen=0.0.0.0:8080 capstone.wsgi:application
worker: celery -A capstone worker --loglevel=info --pool=solo
beat: celery -A capstone beat --loglevel=info