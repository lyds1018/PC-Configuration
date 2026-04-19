# 导入 Django 路由系统的两个核心函数：
# `path()` 定义 URL 规则
# `include()` 引入其他 URL 配置
from django.urls import include, path

# 从当前模块目录导入 `views.py` 模块，即视图模块
from . import views

# 定义 URL 命名空间，用于反向解析 URL（如 `reverse("accounts:login")`
app_name = "accounts"

# URL 路径匹配，Django 会按顺序匹配
urlpatterns = [

    # 空字符串 ""（即根路径 `/accounts/`）
    # 用户访问根目录 → 执行 django 内置登录认证
    path("", include("django.contrib.auth.urls")),

	# 用户访问 → /accounts/register/ 路径 → 执行 views 文件下的 register 函数
    path("register/", views.register, name="register"),

]
