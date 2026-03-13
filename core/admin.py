from django.contrib import admin

from .models import Build, BuildItem, Component, PriceHistory


@admin.register(Component)
class ComponentAdmin(admin.ModelAdmin):
    list_display = ('name', 'brand', 'category', 'price')
    list_filter = ('category', 'brand')
    search_fields = ('name',)


@admin.register(Build)
class BuildAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'status', 'created_at')


@admin.register(BuildItem)
class BuildItemAdmin(admin.ModelAdmin):
    list_display = ('build', 'component', 'quantity')


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ('component', 'price', 'captured_at')