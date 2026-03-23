from django.urls import path

from . import views

app_name = "pc_builder"

urlpatterns = [
    path("", views.build_pc, name="build_pc"),
    path("parts/<str:part_type>/", views.part_list, name="part_list"),
    path(
        "parts/<str:part_type>/select/<int:pk>/",
        views.select_part,
        name="select_part",
    ),
]
