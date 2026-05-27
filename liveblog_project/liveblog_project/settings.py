from pathlib import Path
import os
from django.contrib.messages import constants as messages


MESSAGE_TAGS = {
    messages.ERROR: 'danger',
    messages.WARNING: 'warning',
    messages.SUCCESS: 'success',
    messages.INFO: 'info',
}

BASE_DIR = Path(__file__).resolve().parent.parent

# .env: repo root (../.env) then app dir (./.env); latter overrides for server layouts
try:
    from dotenv import load_dotenv

    for _env_path in (BASE_DIR.parent / '.env', BASE_DIR / '.env'):
        if _env_path.is_file():
            load_dotenv(_env_path, override=True)
except ImportError:
    pass

# SECURITY
DEBUG = os.environ.get('DJANGO_DEBUG', 'False').lower() in ('1', 'true', 'yes')

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '').strip()
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-dev-only-not-for-production'
    else:
        raise ValueError(
            'Set DJANGO_SECRET_KEY in the environment for production deployments.'
        )

_allowed_raw = os.environ.get('DJANGO_ALLOWED_HOSTS', '').strip()
if _allowed_raw:
    ALLOWED_HOSTS = [h.strip() for h in _allowed_raw.split(',') if h.strip()]
elif DEBUG:
    ALLOWED_HOSTS = ['127.0.0.1', 'localhost']
else:
    raise ValueError(
        'Set DJANGO_ALLOWED_HOSTS (comma-separated hostnames, e.g. '
        '"example.com,www.example.com") for production.'
    )

_csrf_origins = os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').strip()
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in _csrf_origins.split(',') if o.strip()
]

if not DEBUG:
    if not CSRF_TRUSTED_ORIGINS:
        raise ValueError(
            'Set DJANGO_CSRF_TRUSTED_ORIGINS for production (comma-separated full URLs), '
            'e.g. https://example.com,https://www.example.com — required behind HTTPS / nginx.'
        )

    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True
    _ssl_redirect = os.environ.get('DJANGO_SECURE_SSL_REDIRECT', 'true').lower()
    SECURE_SSL_REDIRECT = _ssl_redirect in ('1', 'true', 'yes')
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = os.environ.get('SECURE_HSTS_PRELOAD', 'false').lower() in ('1', 'true', 'yes')

# Session / cookies (public site)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax')
SESSION_COOKIE_AGE = int(os.environ.get('SESSION_COOKIE_AGE', str(60 * 60 * 24 * 14)))  # 14 days
SESSION_SAVE_EVERY_REQUEST = os.environ.get('SESSION_SAVE_EVERY_REQUEST', '').lower() in (
    '1',
    'true',
    'yes',
)

# django-ratelimit: use default cache (Redis in prod when REDIS_URL set)
RATELIMIT_USE_CACHE = os.environ.get('RATELIMIT_USE_CACHE', 'default')
RATELIMIT_LOGIN_RATE = os.environ.get('RATELIMIT_LOGIN_RATE', '5/15m')
# security_middleware reads DJANGO_SECURITY_CSP / DJANGO_SECURITY_CSP_REPORT_ONLY.
RATELIMIT_REGISTER_RATE = os.environ.get('RATELIMIT_REGISTER_RATE', '5/h')
RATELIMIT_SEARCH_RATE = os.environ.get('RATELIMIT_SEARCH_RATE', '60/m')
RATELIMIT_SEARCH_SUGGEST_RATE = os.environ.get('RATELIMIT_SEARCH_SUGGEST_RATE', '60/m')
RATELIMIT_TRENDING_RATE = os.environ.get('RATELIMIT_TRENDING_RATE', '120/m')
RATELIMIT_ITEM_COUNTERS_RATE = os.environ.get('RATELIMIT_ITEM_COUNTERS_RATE', '90/m')
RATELIMIT_SEARCH_HISTORY_RATE = os.environ.get('RATELIMIT_SEARCH_HISTORY_RATE', '120/m')
RATELIMIT_REPORT_POST_RATE = os.environ.get('RATELIMIT_REPORT_POST_RATE', '40/m')

SECURITY_HEADERS_ENABLED = os.environ.get('DJANGO_SECURITY_HEADERS', 'true').lower() in (
    '1',
    'true',
    'yes',
    '',
)

# Applications
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django.contrib.sitemaps',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.apple',
    # Third-party
    'rest_framework',
    # Local apps
    'admin_panel',
    'smart_blog.apps.SmartBlogConfig',
    'login',
    'mindset.apps.MindsetConfig',
    'pages.apps.PagesConfig',
    'backups',
]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'liveblog_project.security_middleware.SecurityHeadersMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'liveblog_project.security_middleware.AdminAuditMiddleware',
    'login.middleware.UserOnlineMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Manifest storage fails collectstatic if any referenced file (e.g. *.js.map) is missing.
if os.environ.get('DJANGO_MANIFEST_STATICFILES', 'true').lower() in ('1', 'true', 'yes'):
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
else:
    STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

ROOT_URLCONF = 'liveblog_project.urls'

# Templates
_TEMPLATE_LOADERS = [
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "admin_panel" / "templates", BASE_DIR / "templates"],
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'login.context_processors.user_obj_context',
                'login.context_processors.turnstile_context',
                'login.context_processors.oauth_buttons_context',
                'smart_blog.context_processors.notifications_context',
                'smart_blog.context_processors.spellcheck_context',
                'smart_blog.context_processors.nav_categories_context',
                'smart_blog.context_processors.post_publish_limit_context',
                'admin_panel.context_processors.admin_online_count',
            ],
            'loaders': [
                ('django.template.loaders.cached.Loader', _TEMPLATE_LOADERS),
            ] if not DEBUG else _TEMPLATE_LOADERS,
        },
    },
]


WSGI_APPLICATION = 'liveblog_project.wsgi.application'


# Database — PostgreSQL in production; SQLite only for explicit local dev (never in prod)
_use_sqlite = os.environ.get('DJANGO_USE_SQLITE', '').lower() in ('1', 'true', 'yes')
if _use_sqlite:
    if not DEBUG:
        raise ValueError(
            'DJANGO_USE_SQLITE is only valid with DJANGO_DEBUG=true. '
            'Use PostgreSQL on the server.'
        )
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    _db_user = os.environ.get('DJANGO_DB_USER') or os.environ.get('USER', 'postgres')
    _db_password = os.environ.get('DJANGO_DB_PASSWORD', '')
    if not _db_password:
        raise ValueError(
            'DJANGO_DB_PASSWORD is not set. Set PostgreSQL credentials in the environment, '
            'or for local dev without Postgres set DJANGO_DEBUG=true and DJANGO_USE_SQLITE=true.'
        )
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.environ.get('DJANGO_DB_NAME', 'liveblog'),
            'USER': _db_user,
            'PASSWORD': _db_password,
            'HOST': os.environ.get('DJANGO_DB_HOST', 'localhost'),
            'PORT': os.environ.get('DJANGO_DB_PORT', '5432'),
            'OPTIONS': {'connect_timeout': 10},
            'CONN_MAX_AGE': int(os.environ.get('DJANGO_DB_CONN_MAX_AGE', '60')),
            'CONN_HEALTH_CHECKS': True,
        }
    }


# Password validators
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# django-allauth (social login uses /accounts/…; password login stays at /login/)
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_LOGIN_METHODS = {'username', 'email'}
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_ADAPTER = 'login.adapters.AccountAdapter'
SOCIALACCOUNT_ADAPTER = 'login.adapters.CustomSocialAccountAdapter'
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_LOGOUT_REDIRECT_URL = '/login/'
ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'http' if DEBUG else 'https'

_goog_cid = os.environ.get('GOOGLE_OAUTH_CLIENT_ID', '').strip()
_goog_secret = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET', '').strip()
_apple_cid = os.environ.get('APPLE_CLIENT_ID', '').strip()
_apple_key_id = os.environ.get('APPLE_KEY_ID', '').strip()
_apple_team = os.environ.get('APPLE_TEAM_ID', '').strip()
_apple_pk = os.environ.get('APPLE_PRIVATE_KEY', '').strip().replace('\\n', '\n')

SOCIALACCOUNT_PROVIDERS: dict = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'OAUTH_PKCE_ENABLED': True,
    },
}

if _goog_cid and _goog_secret:
    SOCIALACCOUNT_PROVIDERS['google']['APP'] = {
        'client_id': _goog_cid,
        'secret': _goog_secret,
        'key': '',
    }

if _apple_cid and _apple_key_id and _apple_team and _apple_pk:
    SOCIALACCOUNT_PROVIDERS['apple'] = {
        'APPS': [
            {
                'client_id': _apple_cid,
                'secret': _apple_key_id,
                'key': _apple_team,
                'settings': {'certificate_key': _apple_pk},
            }
        ]
    }

SOCIALACCOUNT_GOOGLE_ENABLED = bool(_goog_cid and _goog_secret)
SOCIALACCOUNT_APPLE_ENABLED = bool(
    _apple_cid and _apple_key_id and _apple_team and _apple_pk
)

# Cloudflare Turnstile (optional; registration check in login.views.auth_views)
TURNSTILE_SITE_KEY = os.environ.get('TURNSTILE_SITE_KEY', '').strip()
TURNSTILE_SECRET_KEY = os.environ.get('TURNSTILE_SECRET_KEY', '').strip()

# Localization
LANGUAGE_CODE = 'en'
TIME_ZONE = 'Asia/Tashkent'  # or 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'

# admin_panel assets live in admin_panel/static/ — collected via AppDirectoriesFinder only.
# Listing the same path here duplicates every file and triggers collectstatic warnings.
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# django-compressor подключаем только если пакет установлен — на проде он есть,
# локально его может не быть (отсутствует в requirements*.txt). В DEBUG также
# отключаем offline-компрессию: иначе шаблоны с {% compress %} падают
# без предварительного `manage.py compress`.
try:
    import compressor  # noqa: F401
except ImportError:
    COMPRESS_ENABLED = False
    COMPRESS_OFFLINE = False
else:
    INSTALLED_APPS.append('compressor')
    STATICFILES_FINDERS.append('compressor.finders.CompressorFinder')
    COMPRESS_ENABLED = not DEBUG
    COMPRESS_OFFLINE = not DEBUG
    COMPRESS_CSS_FILTERS = ['compressor.filters.cssmin.rCSSMinFilter']
    COMPRESS_JS_FILTERS = ['compressor.filters.jsmin.rJSMinFilter']


# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / "media"

# Backups (outside media/static, not publicly accessible)
# Archive files directory (not the backups app package)
BACKUPS_ROOT = BASE_DIR / "backup_archives"
BACKUP_MAX_COUNT = 20
BACKUP_DAILY_COUNT = 7
BACKUP_WEEKLY_COUNT = 4
BACKUP_MONTHLY_COUNT = 12

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# django.contrib.sites — canonical domain for sitemap absolute URLs (update Site in admin after deploy)
SITE_ID = 1

# Cache (LocMem for dev; set REDIS_URL + django-redis for production)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'liveblog-default',
    }
}
_redis_cache_url = os.environ.get('REDIS_URL') or os.environ.get('DJANGO_CACHE_REDIS_URL')
if _redis_cache_url:
    try:
        import django_redis  # noqa: F401  # type: ignore[import-untyped]

        CACHES = {
            'default': {
                'BACKEND': 'django_redis.cache.RedisCache',
                'LOCATION': _redis_cache_url,
                'OPTIONS': {
                    'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                },
            }
        }
    except ImportError:
        pass

# Celery (broker Redis by default; requires celery package)
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', CELERY_BROKER_URL)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

try:
    from datetime import timedelta

    from celery.schedules import crontab

    CELERY_BEAT_SCHEDULE = {
        'update-trending': {
            'task': 'smart_blog.tasks.update_trending',
            'schedule': timedelta(minutes=12),
        },
        'rollup-hourly-stats': {
            'task': 'smart_blog.tasks.rollup_hourly_stats',
            'schedule': crontab(minute=7),
        },
        'prune-view-events': {
            'task': 'smart_blog.tasks.prune_view_events',
            'schedule': crontab(hour=3, minute=30),
        },
    }
except ImportError:
    CELERY_BEAT_SCHEDULE = {}

# Trending JSON cache TTL (seconds); 300–600 matches “5–10 min” refresh window
TRENDING_API_CACHE_SECONDS = int(os.environ.get("TRENDING_API_CACHE_SECONDS", "420"))
# Posts with publish anchor older than this many days are excluded from In trend scoring
TRENDING_ACTIVE_DAYS = int(os.environ.get("TRENDING_ACTIVE_DAYS", "7"))

# Admin panel login redirect
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'

# Spellcheck language (ru/en) - used by spellcheck.js via data-spellcheck-lang
SPELLCHECK_LANG = os.environ.get('SPELLCHECK_LANG', 'en')

# OpenAI moderation (admin Assistant analyzer + tag validation)
# Empty key -> openai_moderator becomes a no-op (deterministic checks still run)
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '').strip()
OPENAI_MODERATION_MODEL = os.environ.get('OPENAI_MODERATION_MODEL', 'omni-moderation-latest')
OPENAI_CLASSIFY_MODEL = os.environ.get('OPENAI_CLASSIFY_MODEL', 'gpt-4o-mini')
try:
    OPENAI_CONFIDENCE_THRESHOLD = float(os.environ.get('OPENAI_CONFIDENCE_THRESHOLD', '0.5'))
except ValueError:
    OPENAI_CONFIDENCE_THRESHOLD = 0.5
try:
    OPENAI_MAX_INPUT_CHARS = int(os.environ.get('OPENAI_MAX_INPUT_CHARS', '8000'))
except ValueError:
    OPENAI_MAX_INPUT_CHARS = 8000
try:
    OPENAI_REQUEST_TIMEOUT = float(os.environ.get('OPENAI_REQUEST_TIMEOUT', '20'))
except ValueError:
    OPENAI_REQUEST_TIMEOUT = 20.0
# Bulk-analyze tuning: batch size for moderation API (single request handles
# many inputs) and thread count for the per-text classifier fallback.
try:
    OPENAI_BATCH_SIZE = int(os.environ.get('OPENAI_BATCH_SIZE', '32'))
except ValueError:
    OPENAI_BATCH_SIZE = 32
try:
    OPENAI_PARALLELISM = int(os.environ.get('OPENAI_PARALLELISM', '8'))
except ValueError:
    OPENAI_PARALLELISM = 8
# Classifier (gpt-4o-mini JSON) catches obfuscated forbidden words but
# costs an extra request per item. Disable for speed when the deterministic
# blocklist + Moderation API are sufficient.
OPENAI_USE_CLASSIFIER = os.environ.get('OPENAI_USE_CLASSIFIER', 'true').lower() in (
    '1', 'true', 'yes', 'on',
)

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'backups': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'django.security': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'security.admin': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

if DEBUG:
    try:
        import debug_toolbar  # noqa: F401
    except ImportError:
        pass
    else:
        INSTALLED_APPS += ['debug_toolbar']
        MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
        INTERNAL_IPS = ['127.0.0.1']
