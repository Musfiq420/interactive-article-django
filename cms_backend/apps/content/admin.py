from django.contrib import admin

from .models import Article, ExpandableSection, InteractiveElement


class InteractiveElementInline(admin.StackedInline):
    model = InteractiveElement
    extra = 1


class ExpandableSectionInline(admin.TabularInline):
    model = ExpandableSection
    extra = 1
    ordering = ("order",)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "created_by", "created_at", "updated_at")
    list_filter = ("created_at", "updated_at")
    search_fields = ("title", "slug", "content", "created_by__username")
    prepopulated_fields = {"slug": ("title",)}
    inlines = (InteractiveElementInline, ExpandableSectionInline)


@admin.register(InteractiveElement)
class InteractiveElementAdmin(admin.ModelAdmin):
    list_display = ("key", "display_text", "type", "article", "created_at")
    list_filter = ("type", "created_at")
    search_fields = ("key", "display_text", "description", "article__title")


@admin.register(ExpandableSection)
class ExpandableSectionAdmin(admin.ModelAdmin):
    list_display = ("title", "article", "order")
    list_filter = ("article",)
    search_fields = ("title", "content", "article__title")
    ordering = ("article", "order")
