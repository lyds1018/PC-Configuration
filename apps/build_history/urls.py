from django.urls import path

from . import views

app_name = "build_history"

# URL 路由配置
urlpatterns = [
    path("", views.history_list, name="history_list"),  # 历史方案列表
    path("<int:history_id>/", views.history_detail, name="history_detail"),  # 方案详情页面
    path(
        "<int:history_id>/delete/", views.delete_history, name="delete_history"
    ),  # 删除方案
    path("save/diy/", views.save_diy_build, name="save_diy_build"),  # 保存 DIY 方案
    path(
        "save/recommend/<int:index>/",
        views.save_recommend_combo,
        name="save_recommend_combo",
    ),  # 保存推荐方案
]
