from decimal import Decimal
from django.conf import settings
from django.db import models


class Component(models.Model):
    name = models.CharField(max_length=200)
    brand = models.CharField(max_length=80, blank=True)
    category = models.CharField(max_length=80)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    image_url = models.URLField(blank=True)
    specs = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('category', 'name')
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} ({self.category})"

    @property
    def price_or_zero(self) -> Decimal:
        return self.price or Decimal('0.00')


class Build(models.Model):
    STATUS_CHOICES = [
        ('private', '私密'),
        ('public', '公开'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    name = models.CharField(max_length=120)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='private')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def total_price(self) -> Decimal:
        return sum((item.component.price_or_zero for item in self.items.all()), Decimal('0.00'))


class BuildItem(models.Model):
    build = models.ForeignKey(Build, related_name='items', on_delete=models.CASCADE)
    component = models.ForeignKey(Component, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.component.name} x{self.quantity}"


class PriceHistory(models.Model):
    component = models.ForeignKey(Component, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    captured_at = models.DateTimeField()

    class Meta:
        ordering = ['-captured_at']

    def __str__(self):
        return f"{self.component.name} @ {self.price}"