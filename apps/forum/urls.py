from django.urls import path

from . import views

app_name = "forum"

urlpatterns = [
    path("", views.forum_page, name="forum_page"),
    path("actions/create-post/", views.create_post, name="create_post"),
    path("actions/posts/<int:post_id>/comment/", views.add_comment, name="add_comment"),
    path("actions/comments/<int:comment_id>/delete/", views.delete_post_comment, name="delete_post_comment"),
    path("actions/posts/<int:post_id>/like/", views.toggle_like, name="toggle_like"),
    path("actions/posts/<int:post_id>/favorite/", views.toggle_favorite, name="toggle_favorite"),
    path("actions/users/<int:user_id>/follow/", views.toggle_follow, name="toggle_follow"),
    path("actions/posts/<int:post_id>/review/", views.review_post, name="review_post"),
]
