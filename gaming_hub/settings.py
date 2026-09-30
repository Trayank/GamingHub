"""
Django settings for gaming_hub project.
Generated for real-time browser-based multiplayer online gaming platform.
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Security settings
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-gaming-hub-super-secret-key-change-in-production'
)

DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1')

ALLOWED_HOSTS = [
    host.strip() for host in os.environ.get('ALLOWED_HOSTS', '127.0.0.1,localhost,*.vercel.app,*').split(',') if host
]

# Session Engine configuration
if os.environ.get('VERCEL') and not os.environ.get('DATABASE_URL'):
    SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
else:
    SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Application definition
INSTALLED_APPS = [
    'daphne',  # Daphne ASGI server must be listed first for channels
    'channels',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    
    # Allauth & Social Auth Apps
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    
    # Project Modular Apps
    'core.apps.CoreConfig',
    'accounts.apps.AccountsConfig',
    'rooms.apps.RoomsConfig',
    'games.apps.GamesConfig',
]

SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'accounts.utils.GuestUserMiddleware',  # Custom middleware to ensure guest session setup
]

ROOT_URLCONF = 'gaming_hub.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'gaming_hub.wsgi.application'
ASGI_APPLICATION = 'gaming_hub.asgi.application'

# Channel Layers - Redis backend with automatic In-Memory fallback for local dev
REDIS_URL = os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0')
USE_REDIS = os.environ.get('USE_REDIS', 'False').lower() in ('true', '1', 't')

if USE_REDIS:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [REDIS_URL],
            },
        },
    }
else:
    # Default to InMemoryChannelLayer for effortless zero-config local dev
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }

# Database Configuration
if os.environ.get('VERCEL') and not os.environ.get('DATABASE_URL'):
    # In serverless Vercel environments without external DB, use writable /tmp directory for SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': Path('/tmp/db.sqlite3'),
        }
    }
elif os.environ.get('DATABASE_URL', '').strip():
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.config(
            default=os.environ['DATABASE_URL'],
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Custom User Model
AUTH_USER_MODEL = 'accounts.User'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Google Social Account Provider Settings
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': os.environ.get('GOOGLE_CLIENT_ID', ''),
            'secret': os.environ.get('GOOGLE_CLIENT_SECRET', ''),
            'key': ''
        },
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        }
    }
}

SOCIALACCOUNT_AUTO_SIGNUP = True
ACCOUNT_LOGIN_METHODS = {'email', 'username'}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

WHITENOISE_MANIFEST_STRICT = os.environ.get('WHITENOISE_MANIFEST_STRICT', 'False').lower() in ('true', '1', 't')

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Redirects
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'rooms:lobby'
LOGOUT_REDIRECT_URL = 'core:landing'
