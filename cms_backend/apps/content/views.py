from django.db.models import Count, Prefetch
from rest_framework import status, viewsets
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from .models import Article, ExpandableSection, InteractiveElement
from .permissions import IsAdminOrReadOnly
from .serializers import (
    ArticleSerializer,
    ExpandableSectionSerializer,
    InteractiveElementSerializer,
)


class ArticleViewSet(viewsets.ModelViewSet):
    queryset = (
        Article.objects.select_related("created_by")
        .prefetch_related(
            Prefetch("interactives", queryset=InteractiveElement.objects.order_by("created_at")),
            Prefetch("sections", queryset=ExpandableSection.objects.order_by("order", "id")),
        )
        .annotate(interactive_count=Count("interactives"))
    )
    serializer_class = ArticleSerializer
    permission_classes = (IsAdminOrReadOnly,)
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    search_fields = ("title", "slug", "content")
    ordering_fields = ("created_at", "updated_at", "title")
    ordering = ("-created_at",)


class InteractiveElementViewSet(viewsets.ModelViewSet):
    queryset = InteractiveElement.objects.select_related("article")
    serializer_class = InteractiveElementSerializer
    permission_classes = (IsAdminOrReadOnly,)
    lookup_field = "key"

    def create(self, request, *args, **kwargs):
        article_id = request.data.get("article")
        if not article_id:
            raise ValidationError({"article": "This field is required."})
        return super().create(request, *args, **kwargs)

    def get_object(self):
        key = self.kwargs[self.lookup_field]
        queryset = self.get_queryset().filter(key=key)

        article_slug = self.request.query_params.get("article")
        if article_slug:
            queryset = queryset.filter(article__slug=article_slug)

        count = queryset.count()
        if count == 0:
            raise NotFound("No interactive element found for the given key.")
        if count > 1:
            raise ValidationError(
                {"article": "Multiple results found. Pass ?article=<article-slug> to disambiguate."}
            )
        return queryset.first()


class ExpandableSectionViewSet(viewsets.ModelViewSet):
    queryset = ExpandableSection.objects.select_related("article")
    serializer_class = ExpandableSectionSerializer
    permission_classes = (IsAdminOrReadOnly,)
    search_fields = ("title", "content", "article__title")
    ordering_fields = ("order", "id")
    ordering = ("order", "id")

    def create(self, request, *args, **kwargs):
        article_id = request.data.get("article")
        if not article_id:
            raise ValidationError({"article": "This field is required."})
        return super().create(request, *args, **kwargs)
