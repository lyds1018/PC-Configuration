from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('builder/', views.builder_home, name='builder'),
    path('builder/category/<str:category>/', views.category_list, name='category_list'),
    path('builder/add/<int:component_id>/', views.add_to_builder, name='add_to_builder'),
    path('builder/remove/<str:category>/', views.remove_from_builder, name='remove_from_builder'),
    path('accounts/register/', views.register, name='register'),
]