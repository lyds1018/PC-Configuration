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
    list_display = ("id", "title", "author", "section", "status", "published_at", "created_at")
    list_filter = ("section", "status")
    search_fields = ("title", "content", "author__username")


admin.site.register(ForumTag)
admin.site.register(ForumComment)
admin.site.register(ForumPostLike)
admin.site.register(ForumPostFavorite)
admin.site.register(ForumUserFollow)
