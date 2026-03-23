from django.urls import path

from . import views

app_name = "recommender"

urlpatterns = [
    path("", views.recommend, name="index"),
]
