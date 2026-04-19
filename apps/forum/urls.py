from django.urls import path

from . import views

app_name = "forum"

# URL 路由配置
urlpatterns = [
    path("", views.forum_page, name="forum_page"),  # 论坛主页
    path(
        "actions/upload-image/", views.upload_editor_image, name="upload_editor_image"
    ),  # 上传图片
    path("actions/create-post/", views.create_post, name="create_post"),  # 创建帖子
    path(
        "actions/posts/<int:post_id>/edit/", views.edit_post, name="edit_post"
    ),  # 编辑帖子
    path(
        "actions/posts/<int:post_id>/delete/", views.delete_post, name="delete_post"
    ),  # 删除帖子
    path(
        "actions/posts/<int:post_id>/comment/", views.add_comment, name="add_comment"
    ),  # 添加评论
    path(
        "actions/comments/<int:comment_id>/delete/",
        views.delete_post_comment,
        name="delete_post_comment",
    ),  # 删除评论
    path(
        "actions/posts/<int:post_id>/like/", views.toggle_like, name="toggle_like"
    ),  # 点赞
    path(
        "actions/posts/<int:post_id>/favorite/",
        views.toggle_favorite,
        name="toggle_favorite",
    ),  # 收藏
    path(
        "actions/users/<int:user_id>/follow/", views.toggle_follow, name="toggle_follow"
    ),  # 关注
    path(
        "actions/posts/<int:post_id>/review/", views.review_post, name="review_post"
    ),  # 审核帖子
]
