from django.urls import path

from . import views

app_name = "build_history"

urlpatterns = [
    path("", views.history_list, name="history_list"),
    path("<int:history_id>/", views.history_detail, name="history_detail"),
    path("<int:history_id>/delete/", views.delete_history, name="delete_history"),
    path("save/diy/", views.save_diy_build, name="save_diy_build"),
    path("save/recommend/<int:index>/", views.save_recommend_combo, name="save_recommend_combo"),
]
