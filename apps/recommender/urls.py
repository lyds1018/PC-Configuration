from django.urls import path

from . import views

app_name = "recommender"

urlpatterns = [
    path("", views.recommend_page, name="recommend_page"),
    path("result/", views.recommend_result_page, name="recommend_result_page"),
    path("result-data/", views.recommend_result_data, name="recommend_result_data"),
]
