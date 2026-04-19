from django.urls import path

from . import views

# 应用命名空间
app_name = "recommender"

# URL 路由配置
urlpatterns = [
    path("", views.recommend_page, name="recommend_page"),  # 推荐表单页面
    path(
        "result/", views.recommend_result_page, name="recommend_result_page"
    ),  # 推荐结果页面
    path(
        "result-data/", views.recommend_result_data, name="recommend_result_data"
    ),  # 推荐结果数据接口
]
