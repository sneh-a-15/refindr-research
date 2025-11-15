import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

# Load local .env for development (do NOT commit .env)
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# Use environment variables (safe for production)
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-i_(r9n_$nb3$@yaowv()-rc%!z-mc+x#1en0&*z^x^uc263=^q'  # local fallback only
)

DEBUG = os.environ.get('DEBUG', 'true').lower() in ('1', 'true', 'yes')

# ALLOWED_HOSTS: comma-separated env var (e.g. "example.com,127.0.0.1")
# _allowed_hosts = os.environ.get('ALLOWED_HOSTS', '')
# if _allowed_hosts:
#     ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts.split(',') if h.strip()]
# else:
#     # sensible local defaults
ALLOWED_HOSTS = ['refindr-research.onrender.com','localhost', '127.0.0.1']

# Application definition

INSTALLED_APPS = [
    'searchapp',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tailwind',
    'theme',
    'widget_tweaks',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise should be right after SecurityMiddleware
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'papersearch.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'papersearch.wsgi.application'

# Database
# Use DATABASE_URL if provided (suitable for Render/Railway/etc).
# Fallback to local Postgres credentials you had.
DATABASE_URL_FALLBACK = os.environ.get(
    'DATABASE_URL',
    'postgres://postgres:1234@localhost:5432/refindr'
)
DATABASES = {
    'default': dj_database_url.parse(DATABASE_URL_FALLBACK, conn_max_age=600)
}

# If you prefer sqlite local fallback when no DB URL, you could instead:
# if not os.environ.get('DATABASE_URL'):
#     DATABASES = {
#         'default': {
#             'ENGINE': 'django.db.backends.sqlite3',
#             'NAME': BASE_DIR / 'db.sqlite3',
#         }
#     }

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# Use WhiteNoise in production
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

STATICFILES_DIRS = [
    BASE_DIR / "theme" / "static",                # your built CSS sits here
    BASE_DIR / "theme" / "static_src" / "src",    # Tailwind source (optional)
]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Tailwind config
TAILWIND_APP_NAME = 'theme'
NPM_BIN_PATH = r"C:\Program Files\nodejs\npm.cmd"

INTERNAL_IPS = [
    "127.0.0.1",
]

# helper to get env var with default
def get_env_variable(var_name, default=''):
    return os.environ.get(var_name, default)

# Academic API Configuration
ACADEMIC_APIS = {
    'GOOGLE_SCHOLAR': {
        'API_KEY': get_env_variable('GOOGLE_SCHOLAR_API_KEY', ''),
        'SEARCH_ENGINE_ID': get_env_variable('GOOGLE_SCHOLAR_SEARCH_ENGINE_ID', ''),
        'BASE_URL': 'https://www.searchapi.io/api/v1/search',
        'ENABLED': get_env_variable('GOOGLE_SCHOLAR_ENABLED', 'True').lower() == 'true'
    },
    'SPRINGER': {
        'API_KEY': get_env_variable('SPRINGER_API_KEY'),
        'BASE_URL': 'http://api.springernature.com/meta/v2/json',
        'ENABLED': get_env_variable('SPRINGER_ENABLED', 'True').lower() == 'true'
    },
    'PUBMED': {
        'ENABLED' : get_env_variable('PUBMED_ENABLED', 'True').lower() == 'true'
    },
    'ELSEVIER': {
        'API_KEY': get_env_variable('ELSEVIER_API_KEY'),
        'INST_TOKEN': get_env_variable('ELSEVIER_INST_TOKEN', ''),  # Optional institutional token
        'BASE_URL': 'https://api.elsevier.com/content/search/scopus',
        'ENABLED': get_env_variable('ELSEVIER_ENABLED', 'True').lower() == 'true'
    },
    'ARXIV': {
        'BASE_URL': 'http://export.arxiv.org/api/query',
        'ENABLED': get_env_variable('ARXIV_ENABLED', 'True').lower() == 'true'
    }
}

# Rate limiting configuration
API_RATE_LIMITS = {
    'GOOGLE_SCHOLAR': 100,
    'SEMANTIC_SCHOLAR': 1000,
    'IEEE_XPLORE': 200,
    'SPRINGER': 5000,
    'ELSEVIER': 20000,
    'ARXIV': float('inf')
}

# Timeout settings
API_TIMEOUTS = {
    'DEFAULT': 10,
    'GOOGLE_SCHOLAR': 15,
    'IEEE_XPLORE': 20,
    'SPRINGER': 15,
    'ELSEVIER': 20
}

# Session and security flags
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Optional: security settings for production (enable via env)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'true').lower() in ('1','true','yes')
CSRF_COOKIE_SECURE = os.environ.get('CSRF_COOKIE_SECURE', 'true').lower() in ('1','true','yes')
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'false').lower() in ('1','true','yes')

