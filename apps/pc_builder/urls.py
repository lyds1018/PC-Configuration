from django.urls import path

from . import views

app_name = "pc_builder"

# URL 路由配置
urlpatterns = [
    path("", views.build_pc, name="build_pc"),  # 首页
    path("parts/<str:part_type>/", views.part_list, name="part_list"),  # 配件列表页面
    path(
        "parts/<str:part_type>/select/<int:pk>/",
        views.select_part,
        name="select_part",
    ),  # 选择配件接口
]
