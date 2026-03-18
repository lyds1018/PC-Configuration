from django.urls import path

from . import views

urlpatterns = [
    path("", views.build_pc, name="build_pc"),
]
