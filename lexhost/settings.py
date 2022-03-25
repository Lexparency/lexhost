import logging

from django.http import HttpResponseGone

from settings import *

DEBUG = True

ALLOWED_HOSTS = ['*']  # TODO: Need to be changed for production
DEFAULT_FROM_EMAIL = 'mail@' + INTERNET_DOMAIN
ROOT_URLCONF = 'lexhost.urls'
APPEND_SLASH = True

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'lexhost' / 'assets' / 'templates'
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# https://docs.djangoproject.com/en/1.9/howto/static-files/
# STATIC_ROOT = BASE_DIR / 'lexhost/assets/static-dist')
STATIC_URL = '/static/'

# Extra places for collectstatic to find static files.
STATICFILES_DIRS = [
    BASE_DIR / 'lexhost' / 'assets' / 'static'
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


SECRET_KEY = 'asdfsdf'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'lex.sqlite3',
    }
}

WSGI_APPLICATION = 'lexhost.wsgi.application'
