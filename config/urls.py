from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls", namespace="accounts")),
    path("pc-builder/", include("pc_builder.urls", namespace="pc_builder")),
    path("recommender/", include("recommender.urls", namespace="recommender")),
    path("history/", include("build_history.urls", namespace="build_history")),
    path("forum/", include("forum.urls", namespace="forum")),
]

# 开发环境下提供媒体文件访问
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# 默认 URL - 重定向到装机页面
urlpatterns += [
    path("", lambda request: redirect("pc_builder:build_pc")),
]
