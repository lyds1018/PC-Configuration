from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class ForumTag(models.Model):
    name = models.CharField(max_length=30, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "forum_tag"
        ordering = ("name",)

    def __str__(self):
        return self.name


class ForumPost(models.Model):
    SECTION_EXPERIENCE = "experience"
    SECTION_HELP = "help"
    SECTION_NEWS = "news"
    SECTION_CHOICES = (
        (SECTION_EXPERIENCE, "经验分享"),
        (SECTION_HELP, "问题求助"),
        (SECTION_NEWS, "资讯分析"),
    )

    STATUS_PENDING = "pending"
    STATUS_PUBLISHED = "published"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = (
        (STATUS_PENDING, "审核中"),
        (STATUS_PUBLISHED, "正常"),
        (STATUS_REJECTED, "已驳回"),
    )

    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="forum_posts")
    title = models.CharField(max_length=200)
    section = models.CharField(max_length=20, choices=SECTION_CHOICES)
    content = models.TextField()
    tags = models.ManyToManyField(ForumTag, blank=True, related_name="posts")

    view_count = models.PositiveIntegerField(default=0)
    like_count = models.PositiveIntegerField(default=0)
    comment_count = models.PositiveIntegerField(default=0)
    favorite_count = models.PositiveIntegerField(default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    reviewed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_forum_posts",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reject_reason = models.CharField(max_length=255, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "forum_post"
        ordering = ("-published_at", "-created_at")
        indexes = [
            models.Index(fields=["section", "status"]),
            models.Index(fields=["status", "published_at"]),
            models.Index(fields=["author", "status"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.author_id})"


class ForumComment(models.Model):
    post = models.ForeignKey(ForumPost, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name="forum_comments")
    content = models.TextField()
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "forum_comment"
        ordering = ("created_at",)

    def __str__(self):
        return f"comment:{self.id} post:{self.post_id}"


class ForumPostLike(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="forum_post_likes")
    post = models.ForeignKey(ForumPost, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "forum_post_like"
        constraints = [
            models.UniqueConstraint(fields=["user", "post"], name="uniq_forum_like_user_post"),
        ]


class ForumPostFavorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="forum_post_favorites")
    post = models.ForeignKey(ForumPost, on_delete=models.CASCADE, related_name="favorites")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "forum_post_favorite"
        constraints = [
            models.UniqueConstraint(fields=["user", "post"], name="uniq_forum_favorite_user_post"),
        ]


class ForumUserFollow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name="forum_following")
    followee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="forum_followers")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "forum_user_follow"
        constraints = [
            models.UniqueConstraint(fields=["follower", "followee"], name="uniq_forum_follow_pair"),
            models.CheckConstraint(check=~models.Q(follower=models.F("followee")), name="chk_forum_no_self_follow"),
        ]
