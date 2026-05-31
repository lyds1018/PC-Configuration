import os
import secrets
import sys
from pathlib import Path

# 将 apps 目录加入 Python 路径
BASE_DIR = Path(__file__).resolve().parent.parent
APPS_DIR = BASE_DIR / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

SECRET_KEY = secrets.token_urlsafe(50)

DEBUG = True

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"

# 默认主键字段类型
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# 语言、时区
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

# 认证配置
LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/pc-builder/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# 静态资源（CSS / JS / 图片）
STATIC_URL = "/static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"

# 媒体文件 (用户上传)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# 允许访问域名
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost,::1,testserver"
    ).split(",")
    if host.strip()
]

# 应用列表
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 项目应用
    "accounts",
    "pc_builder",
    "recommender",
    "build_history",
    "forum",
]

# HTTP 请求处理中间件
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# 模板配置
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],   # 全局模板
        "APP_DIRS": True,   # 应用私有模板
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# 数据库配置
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "pc_db",
        "USER": "root",
        "PASSWORD": "041018",
        "HOST": "127.0.0.1",
        "PORT": "3306",
    }
}

# 密码强度校验器
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]
