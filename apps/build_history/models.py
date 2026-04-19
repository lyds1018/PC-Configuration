'''
构建历史相关的数据模型，
用于存储用户保存的构建历史记录
'''

from django.db import models


class BuildHistory(models.Model):
    SOURCE_DIY = "diy"
    SOURCE_RECOMMEND = "recommend"
    SOURCE_CHOICES = (
        (SOURCE_DIY, "DIY装机"),
        (SOURCE_RECOMMEND, "智能推荐"),
    )

    user = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="saved_build_histories")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    title = models.CharField(max_length=120, blank=True)
    total_price = models.FloatField(default=0.0)
    summary = models.TextField(blank=True)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "build_history"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user_id}:{self.title or self.get_source_display()}"
