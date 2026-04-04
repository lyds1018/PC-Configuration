from django.urls import path

from . import views

app_name = "forum"

urlpatterns = [
    path("", views.forum_page, name="forum_page"),
    path("actions/upload-image/", views.upload_editor_image, name="upload_editor_image"),
    path("actions/create-post/", views.create_post, name="create_post"),
    path("actions/posts/<int:post_id>/edit/", views.edit_post, name="edit_post"),
    path("actions/posts/<int:post_id>/delete/", views.delete_post, name="delete_post"),
    path("actions/posts/<int:post_id>/comment/", views.add_comment, name="add_comment"),
    path("actions/comments/<int:comment_id>/delete/", views.delete_post_comment, name="delete_post_comment"),
    path("actions/posts/<int:post_id>/like/", views.toggle_like, name="toggle_like"),
    path("actions/posts/<int:post_id>/favorite/", views.toggle_favorite, name="toggle_favorite"),
    path("actions/users/<int:user_id>/follow/", views.toggle_follow, name="toggle_follow"),
    path("actions/posts/<int:post_id>/review/", views.review_post, name="review_post"),
]
