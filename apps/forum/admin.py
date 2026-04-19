"""
论坛模块后台管理配置
"""

from django.contrib import admin

from .models import (
    ForumComment,
    ForumPost,
    ForumPostFavorite,
    ForumPostLike,
    ForumTag,
    ForumUserFollow,
)


@admin.register(ForumPost)
class ForumPostAdmin(admin.ModelAdmin):
    # 列表显示的字段
    list_display = (
        "id",
        "title",
        "author",
        "section",
        "status",
        "published_at",
        "created_at",
    )
    # 侧边栏筛选字段
    list_filter = ("section", "status")
    # 搜索字段
    search_fields = ("title", "content", "author__username")


# 注册其他论坛模型到后台
admin.site.register(ForumTag)  # 标签
admin.site.register(ForumComment)  # 评论
admin.site.register(ForumPostLike)  # 帖子点赞
admin.site.register(ForumPostFavorite)  # 帖子收藏
admin.site.register(ForumUserFollow)  # 用户关注
