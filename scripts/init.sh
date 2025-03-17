#! /bin/bash

pip install mozilla-django-oidc
pip install jwcrypto requests
# Run migrations and create superuser
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser --no-input || true
python manage.py collectstatic --noinput
