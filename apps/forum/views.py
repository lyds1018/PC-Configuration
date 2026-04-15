from collections import defaultdict
from datetime import timedelta
import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.db.models import F, Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import (
    ForumComment,
    ForumPost,
    ForumPostFavorite,
    ForumPostLike,
    ForumTag,
    ForumUserFollow,
)

FORUM_TAB_ALL = "all"
FORUM_TAB_EXPERIENCE = "experience"
FORUM_TAB_HELP = "help"
FORUM_TAB_NEWS = "news"
FORUM_TAB_CREATE = "create"
FORUM_TAB_PROFILE = "profile"
FORUM_TAB_FOLLOWING = "following"
FORUM_TAB_DETAIL = "detail"
FORUM_TAB_MODERATION = "moderation"

PROFILE_VIEW_OVERVIEW = "overview"
PROFILE_VIEW_POSTS = "posts"
PROFILE_VIEW_LIKES = "likes"
PROFILE_VIEW_FAVORITES = "favorites"

FORUM_SORT_NEWEST = "newest"
FORUM_SORT_VIEWS = "views"
FORUM_SORT_LIKES = "likes"
FORUM_SORT_FAVORITES = "favorites"

TAB_TO_SECTION = {
    FORUM_TAB_EXPERIENCE: ForumPost.SECTION_EXPERIENCE,
    FORUM_TAB_HELP: ForumPost.SECTION_HELP,
    FORUM_TAB_NEWS: ForumPost.SECTION_NEWS,
}
SORT_TO_ORDERING = {
    FORUM_SORT_NEWEST: ["-published_at", "-created_at"],
    FORUM_SORT_VIEWS: ["-view_count", "-published_at", "-created_at"],
    FORUM_SORT_LIKES: ["-like_count", "-published_at", "-created_at"],
    FORUM_SORT_FAVORITES: ["-favorite_count", "-published_at", "-created_at"],
}
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_EDITOR_IMAGE_SIZE = 5 * 1024 * 1024


def _redirect_next(request, default_tab=FORUM_TAB_ALL):
    next_url = (request.POST.get("next") or "").strip()
    if next_url.startswith("/forum"):
        return redirect(next_url)
    return redirect(f"{reverse('forum:forum_page')}?tab={default_tab}")


def _parse_tag_names(raw_tags):
    chunks = re.findall(r"[#＃]([^\s#＃,，]+)", raw_tags or "")
    deduped = []
    seen = set()
    for name in chunks:
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(name[:30])
    return deduped[:8]


def _extract_post_form(request):
    return {
        "title": (request.POST.get("title") or "").strip(),
        "section": (request.POST.get("section") or "").strip(),
        "content": (request.POST.get("content") or "").strip(),
        "raw_tags": (request.POST.get("tags") or "").strip(),
    }


def _validate_post_form(form):
    if not form["title"] or not form["content"]:
        return "标题和正文不能为空。"
    if form["section"] not in dict(ForumPost.SECTION_CHOICES):
        return "请选择正确的版块。"
    if form["raw_tags"] and not re.fullmatch(
        r"\s*[#＃][^\s#＃,，]+(?:\s*[，,]\s*[#＃][^\s#＃,，]+)*\s*",
        form["raw_tags"],
    ):
        return "标签格式应为 #内存，#溢价。"
    return ""


def _list_post_queryset(tab, q, sort):
    posts = ForumPost.objects.filter(status=ForumPost.STATUS_PUBLISHED).select_related("author").prefetch_related("tags")
    section = TAB_TO_SECTION.get(tab)
    if section:
        posts = posts.filter(section=section)

    if q:
        posts = posts.filter(
            Q(title__icontains=q) | Q(content__icontains=q) | Q(tags__name__icontains=q)
        ).distinct()

    ordering = SORT_TO_ORDERING.get(sort, SORT_TO_ORDERING[FORUM_SORT_NEWEST])
    return posts.order_by(*ordering)


def _get_detail_context(request, post_id):
    post = get_object_or_404(
        ForumPost.objects.select_related("author", "reviewed_by").prefetch_related("tags"),
        id=post_id,
    )
    if post.status != ForumPost.STATUS_PUBLISHED and not (
        request.user.is_staff or post.author_id == request.user.id
    ):
        raise PermissionError

    is_unpublished_preview = post.status != ForumPost.STATUS_PUBLISHED
    if not is_unpublished_preview:
        ForumPost.objects.filter(id=post.id).update(view_count=F("view_count") + 1)
        post.refresh_from_db()

    comment_rows = (
        ForumComment.objects.filter(post=post)
        .select_related("author", "parent", "parent__author")
        .order_by("created_at")
    )
    root_comments = []
    reply_map = defaultdict(list)
    commenters = set()
    for comment in comment_rows:
        commenters.add(comment.author_id)
        if comment.parent_id:
            reply_map[comment.parent_id].append(comment)
        else:
            root_comments.append(comment)

    liked = ForumPostLike.objects.filter(user=request.user, post=post).exists()
    favorited = ForumPostFavorite.objects.filter(user=request.user, post=post).exists()
    followed_user_ids = set(
        ForumUserFollow.objects.filter(
            follower=request.user,
            followee_id__in=commenters | {post.author_id},
        ).values_list("followee_id", flat=True)
    )

    return {
        "detail_post": post,
        "detail_unpublished_preview": is_unpublished_preview,
        "root_comments": root_comments,
        "reply_map": dict(reply_map),
        "detail_liked": liked,
        "detail_favorited": favorited,
        "followed_user_ids": followed_user_ids,
    }


@login_required
def forum_page(request):
    tab = request.GET.get("tab", FORUM_TAB_ALL)
    if tab == FORUM_TAB_MODERATION and not request.user.is_staff:
        tab = FORUM_TAB_ALL

    q = (request.GET.get("q") or "").strip()
    sort = request.GET.get("sort", FORUM_SORT_NEWEST)
    detail_post_id = request.GET.get("post")

    context = {
        "active_tab": tab,
        "query_text": q,
        "sort_value": sort if sort in SORT_TO_ORDERING else FORUM_SORT_NEWEST,
        "sort_choices": [
            (FORUM_SORT_NEWEST, "发布时间"),
            (FORUM_SORT_VIEWS, "浏览量"),
            (FORUM_SORT_LIKES, "点赞量"),
            (FORUM_SORT_FAVORITES, "收藏量"),
        ],
        "section_labels": dict(ForumPost.SECTION_CHOICES),
        "post_status_labels": dict(ForumPost.STATUS_CHOICES),
    }

    if tab in {FORUM_TAB_ALL, FORUM_TAB_EXPERIENCE, FORUM_TAB_HELP, FORUM_TAB_NEWS}:
        context["posts"] = _list_post_queryset(tab, q, sort)

    elif tab == FORUM_TAB_PROFILE:
        profile_view = (request.GET.get("view") or PROFILE_VIEW_OVERVIEW).strip()
        if profile_view not in {
            PROFILE_VIEW_OVERVIEW,
            PROFILE_VIEW_POSTS,
            PROFILE_VIEW_LIKES,
            PROFILE_VIEW_FAVORITES,
        }:
            profile_view = PROFILE_VIEW_OVERVIEW

        my_posts_qs = ForumPost.objects.filter(author=request.user).prefetch_related("tags").order_by("-created_at")
        week_ago = timezone.now() - timedelta(days=7)
        recent_likes_qs = (
            ForumPostLike.objects.filter(user=request.user, created_at__gte=week_ago, post__status=ForumPost.STATUS_PUBLISHED)
            .select_related("post", "post__author")
            .order_by("-created_at")
        )
        favorites_qs = (
            ForumPostFavorite.objects.filter(user=request.user, post__status=ForumPost.STATUS_PUBLISHED)
            .select_related("post", "post__author")
            .order_by("-created_at")
        )

        my_posts = my_posts_qs if profile_view == PROFILE_VIEW_POSTS else my_posts_qs[:3]
        recent_likes = recent_likes_qs if profile_view == PROFILE_VIEW_LIKES else recent_likes_qs[:5]
        favorites = favorites_qs if profile_view == PROFILE_VIEW_FAVORITES else favorites_qs[:5]

        context.update(
            {
                "profile_view": profile_view,
                "my_posts": my_posts,
                "recent_likes": recent_likes,
                "favorites": favorites,
                "my_posts_total": my_posts_qs.count(),
                "recent_likes_total": recent_likes_qs.count(),
                "favorites_total": favorites_qs.count(),
            }
        )
    elif tab == FORUM_TAB_FOLLOWING:
        followed_user_ids = ForumUserFollow.objects.filter(follower=request.user).values_list("followee_id", flat=True)
        following_posts = (
            ForumPost.objects.filter(
                status=ForumPost.STATUS_PUBLISHED,
                author_id__in=followed_user_ids,
            )
            .select_related("author")
            .prefetch_related("tags")
            .order_by("-published_at", "-created_at")
        )
        context["following_posts"] = following_posts
    elif tab == FORUM_TAB_CREATE:
        editing_post_id = request.GET.get("edit")
        if editing_post_id:
            post = ForumPost.objects.prefetch_related("tags").filter(id=editing_post_id).first()
            if not post:
                messages.error(request, "要编辑的帖子不存在。")
            elif not (request.user.is_staff or post.author_id == request.user.id):
                messages.error(request, "无权限编辑该帖子。")
            else:
                context["editing_post"] = post
                context["editing_tags"] = "，".join(f"#{tag.name}" for tag in post.tags.all())

    elif tab == FORUM_TAB_MODERATION and request.user.is_staff:
        pending_posts = (
            ForumPost.objects.filter(status=ForumPost.STATUS_PENDING)
            .select_related("author")
            .prefetch_related("tags")
            .order_by("created_at")
        )
        context["pending_posts"] = pending_posts

    if (tab == FORUM_TAB_DETAIL or detail_post_id) and detail_post_id:
        try:
            context.update(_get_detail_context(request, int(detail_post_id)))
            context["active_tab"] = FORUM_TAB_DETAIL
        except (ValueError, PermissionError):
            messages.error(request, "帖子不存在或无权访问。")
            context["active_tab"] = FORUM_TAB_ALL

    return render(request, "forum/index.html", context)


@login_required
def create_post(request):
    if request.method != "POST":
        return redirect("forum:forum_page")

    form = _extract_post_form(request)
    form_error = _validate_post_form(form)
    if form_error:
        messages.error(request, form_error)
        return _redirect_next(request, default_tab=FORUM_TAB_CREATE)

    post = ForumPost.objects.create(
        author=request.user,
        title=form["title"][:200],
        section=form["section"],
        content=form["content"],
        status=ForumPost.STATUS_PENDING,
    )

    for tag_name in _parse_tag_names(form["raw_tags"]):
        tag, _ = ForumTag.objects.get_or_create(name=tag_name)
        post.tags.add(tag)

    messages.success(request, "帖子已提交，等待管理员审核。")
    return redirect("forum:forum_page")


@login_required
def edit_post(request, post_id):
    if request.method != "POST":
        return redirect("forum:forum_page")

    post = get_object_or_404(ForumPost.objects.prefetch_related("tags"), id=post_id)
    if not (request.user.is_staff or post.author_id == request.user.id):
        return HttpResponseForbidden("无权限")

    form = _extract_post_form(request)
    form_error = _validate_post_form(form)
    if form_error:
        messages.error(request, form_error)
        return redirect(f"{reverse('forum:forum_page')}?tab=create&edit={post_id}")

    post.title = form["title"][:200]
    post.section = form["section"]
    post.content = form["content"]
    post.status = ForumPost.STATUS_PENDING
    post.reviewed_by = None
    post.reviewed_at = None
    post.reject_reason = ""
    post.published_at = None
    post.save(
        update_fields=[
            "title",
            "section",
            "content",
            "status",
            "reviewed_by",
            "reviewed_at",
            "reject_reason",
            "published_at",
            "updated_at",
        ]
    )

    post.tags.clear()
    for tag_name in _parse_tag_names(form["raw_tags"]):
        tag, _ = ForumTag.objects.get_or_create(name=tag_name)
        post.tags.add(tag)

    messages.success(request, "帖子已更新，并重新进入审核队列。")
    return redirect("forum:forum_page")


@login_required
def delete_post(request, post_id):
    if request.method != "POST":
        return redirect("forum:forum_page")

    post = get_object_or_404(ForumPost, id=post_id)
    if not (request.user.is_staff or post.author_id == request.user.id):
        return HttpResponseForbidden("无权限")

    post.delete()
    messages.success(request, "帖子已删除。")
    return redirect("forum:forum_page")


@login_required
def add_comment(request, post_id):
    if request.method != "POST":
        return redirect("forum:forum_page")

    post = get_object_or_404(ForumPost, id=post_id, status=ForumPost.STATUS_PUBLISHED)
    content = (request.POST.get("content") or "").strip()
    if not content:
        messages.error(request, "评论不能为空。")
        return _redirect_next(request, default_tab=FORUM_TAB_DETAIL)

    parent_id = request.POST.get("parent_id")
    parent = None
    if parent_id:
        parent = ForumComment.objects.filter(id=parent_id, post=post).first()
        if parent and parent.parent_id:
            parent = parent.parent

    ForumComment.objects.create(post=post, author=request.user, content=content, parent=parent)
    ForumPost.objects.filter(id=post.id).update(comment_count=F("comment_count") + 1)

    messages.success(request, "评论成功。")
    return _redirect_next(request, default_tab=FORUM_TAB_DETAIL)


@login_required
def delete_post_comment(request, comment_id):
    if request.method != "POST":
        return redirect("forum:forum_page")

    comment = get_object_or_404(ForumComment.objects.select_related("post", "author", "post__author"), id=comment_id)
    post = comment.post

    if request.user != post.author and request.user != comment.author and not request.user.is_staff:
        return HttpResponseForbidden("无权限")

    ForumComment.objects.filter(Q(id=comment.id) | Q(parent_id=comment.id)).delete()
    remaining_count = ForumComment.objects.filter(post=post).count()
    ForumPost.objects.filter(id=post.id).update(comment_count=remaining_count)

    messages.success(request, "评论已删除。")
    return _redirect_next(request, default_tab=FORUM_TAB_PROFILE)


@login_required
def toggle_like(request, post_id):
    if request.method != "POST":
        return redirect("forum:forum_page")

    post = get_object_or_404(ForumPost, id=post_id, status=ForumPost.STATUS_PUBLISHED)
    like, created = ForumPostLike.objects.get_or_create(user=request.user, post=post)
    if created:
        ForumPost.objects.filter(id=post.id).update(like_count=F("like_count") + 1)
        messages.success(request, "已点赞。")
    else:
        like.delete()
        ForumPost.objects.filter(id=post.id, like_count__gt=0).update(like_count=F("like_count") - 1)
        messages.info(request, "已取消点赞。")

    return _redirect_next(request, default_tab=FORUM_TAB_DETAIL)


@login_required
def toggle_favorite(request, post_id):
    if request.method != "POST":
        return redirect("forum:forum_page")

    post = get_object_or_404(ForumPost, id=post_id, status=ForumPost.STATUS_PUBLISHED)
    favorite, created = ForumPostFavorite.objects.get_or_create(user=request.user, post=post)
    if created:
        ForumPost.objects.filter(id=post.id).update(favorite_count=F("favorite_count") + 1)
        messages.success(request, "已收藏。")
    else:
        favorite.delete()
        ForumPost.objects.filter(id=post.id, favorite_count__gt=0).update(favorite_count=F("favorite_count") - 1)
        messages.info(request, "已取消收藏。")

    return _redirect_next(request, default_tab=FORUM_TAB_DETAIL)


@login_required
def toggle_follow(request, user_id):
    if request.method != "POST":
        return redirect("forum:forum_page")

    if user_id == request.user.id:
        messages.warning(request, "不能关注自己。")
        return _redirect_next(request)

    follow, created = ForumUserFollow.objects.get_or_create(follower=request.user, followee_id=user_id)
    if created:
        messages.success(request, "关注成功。")
    else:
        follow.delete()
        messages.info(request, "已取消关注。")

    return _redirect_next(request)


@login_required
def review_post(request, post_id):
    if request.method != "POST":
        return redirect(f"{reverse('forum:forum_page')}?tab={FORUM_TAB_MODERATION}")
    if not request.user.is_staff:
        return HttpResponseForbidden("仅管理员可操作")

    post = get_object_or_404(ForumPost, id=post_id)
    action = (request.POST.get("action") or "").strip()
    now = timezone.now()

    if action == "approve":
        post.status = ForumPost.STATUS_PUBLISHED
        post.reviewed_by = request.user
        post.reviewed_at = now
        post.reject_reason = ""
        post.published_at = now
        post.save(update_fields=["status", "reviewed_by", "reviewed_at", "reject_reason", "published_at", "updated_at"])
        messages.success(request, "帖子已审核通过。")
    elif action == "reject":
        reject_reason = (request.POST.get("reject_reason") or "").strip()
        post.status = ForumPost.STATUS_REJECTED
        post.reviewed_by = request.user
        post.reviewed_at = now
        post.reject_reason = reject_reason[:255]
        post.save(update_fields=["status", "reviewed_by", "reviewed_at", "reject_reason", "updated_at"])

        ban_user = (request.POST.get("ban_user") or "").strip() == "1"
        if ban_user and post.author.is_active:
            post.author.is_active = False
            post.author.save(update_fields=["is_active"])
            messages.warning(request, f"帖子已驳回，用户 {post.author.username} 已被封禁。")
        else:
            messages.success(request, "帖子已驳回。")
    else:
        messages.error(request, "无效的审核操作。")

    return redirect(f"{reverse('forum:forum_page')}?tab={FORUM_TAB_MODERATION}")


@login_required
def upload_editor_image(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "message": "请求方式不正确。"}, status=405)

    image = request.FILES.get("image")
    if not image:
        return JsonResponse({"ok": False, "message": "未找到上传文件。"}, status=400)
    if image.size > MAX_EDITOR_IMAGE_SIZE:
        return JsonResponse({"ok": False, "message": "图片大小不能超过 5MB。"}, status=400)

    file_name = (image.name or "").lower()
    ext = "." + file_name.split(".")[-1] if "." in file_name else ""
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return JsonResponse({"ok": False, "message": "仅支持 jpg/png/gif/webp 图片。"}, status=400)
    if not (image.content_type or "").startswith("image/"):
        return JsonResponse({"ok": False, "message": "上传文件不是图片。"}, status=400)

    timestamp = timezone.now()
    save_path = (
        f"forum/editor/{request.user.id}/{timestamp.strftime('%Y/%m')}/"
        f"{timestamp.strftime('%Y%m%d%H%M%S%f')}{ext}"
    )
    stored_path = default_storage.save(save_path, image)
    image_url = default_storage.url(stored_path)
    return JsonResponse({"ok": True, "url": image_url})
