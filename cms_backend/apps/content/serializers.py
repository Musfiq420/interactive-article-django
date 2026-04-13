import re

from django.db import transaction
from rest_framework import serializers
import logging
logger = logging.getLogger(__name__)

from .models import Article, ExpandableSection, InteractiveElement
from .validators import (
    AUDIO_EXTENSIONS,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    validate_file_extension,
    validate_interactive_payload,
    validate_youtube_url,
)


INTERACTIVE_KEY_PATTERN = re.compile(r'data-key=["\'](?P<key>[^"\']+)["\']')


class MediaURLMixin:
    def _build_media_url(self, value):
        if not value:
            return None
        request = self.context.get("request")
        url = value.url
        return request.build_absolute_uri(url) if request else url


class InteractiveElementSerializer(MediaURLMixin, serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    audio = serializers.SerializerMethodField()
    video = serializers.SerializerMethodField()
    image_upload = serializers.ImageField(write_only=True, source="image", required=False, allow_null=True)
    audio_upload = serializers.FileField(write_only=True, source="audio", required=False, allow_null=True)
    video_upload = serializers.FileField(write_only=True, source="video", required=False, allow_null=True)
    # Writable for direct /api/interactives/ create; parent ArticleSerializer still passes article via context/save.
    article = serializers.PrimaryKeyRelatedField(
        queryset=Article.objects.all(),
        required=False,
    )

    class Meta:
        model = InteractiveElement
        fields = (
            "id",
            "key",
            "article",
            "display_text",
            "type",
            "image",
            "audio",
            "video",
            "image_upload",
            "audio_upload",
            "video_upload",
            "youtube_url",
            "description",
            "metadata",
            "created_at",
        )
        read_only_fields = ("id", "created_at", "image", "audio", "video")
        # We enforce article+key uniqueness manually in validate() to support nested upserts
        # where article comes from parent context instead of payload.
        validators = []
        extra_kwargs = {
            "youtube_url": {"required": False, "allow_blank": True},
            "description": {"required": False, "allow_blank": True},
            "metadata": {"required": False, "allow_null": True},
        }

    def get_image(self, obj):
        return self._build_media_url(obj.image)

    def get_audio(self, obj):
        return self._build_media_url(obj.audio)

    def get_video(self, obj):
        return self._build_media_url(obj.video)

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        interactive_type = attrs.get("type", getattr(instance, "type", None))
        allow_missing_media_for_upsert = bool(
            self.context.get("allow_missing_media_for_upsert") and instance is None
        )

        payload = {
            "image": attrs.get("image", getattr(instance, "image", None)),
            "audio": attrs.get("audio", getattr(instance, "audio", None)),
            "video": attrs.get("video", getattr(instance, "video", None)),
            "youtube_url": attrs.get("youtube_url", getattr(instance, "youtube_url", "")),
            "description": attrs.get("description", getattr(instance, "description", "")),
            "metadata": attrs.get("metadata", getattr(instance, "metadata", None)),
        }

        validate_file_extension(payload["image"], IMAGE_EXTENSIONS, "Image")
        validate_file_extension(payload["audio"], AUDIO_EXTENSIONS, "Audio")
        validate_file_extension(payload["video"], VIDEO_EXTENSIONS, "Video")
        validate_youtube_url(payload["youtube_url"])
        if allow_missing_media_for_upsert:
            # Parent ArticleSerializer will upsert by id/key, then validate again with instance context.
            if interactive_type not in {"image", "audio", "video", "youtube", "text"}:
                raise serializers.ValidationError({"type": "Unsupported interactive type."})
        else:
            validate_interactive_payload(interactive_type, payload)

        article = (
            self.context.get("article")
            or attrs.get("article")
            or getattr(instance, "article", None)
        )
        key = attrs.get("key", getattr(instance, "key", None))
        if article and key:
            qs = InteractiveElement.objects.filter(article=article, key=key)
            if instance:
                qs = qs.exclude(pk=instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"key": "This key must be unique within the article."}
                )

        return attrs

class ExpandableSectionSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    article = serializers.PrimaryKeyRelatedField(
        queryset=Article.objects.all(),
        required=False,
        write_only=True,
    )

    class Meta:
        model = ExpandableSection
        fields = ("id", "article", "title", "content", "order")



class ArticleSerializer(serializers.ModelSerializer):
    interactives = InteractiveElementSerializer(many=True, required=False)
    sections = ExpandableSectionSerializer(many=True, required=False)
    created_by = serializers.StringRelatedField(read_only=True)
    class Meta:
        model = Article
        fields = (
            "id",
            "title",
            "slug",
            "content",
            "created_by",
            "created_at",
            "updated_at",
            "interactives",
            "sections",
        )
        read_only_fields = ("id", "created_by", "created_at", "updated_at")
        extra_kwargs = {
            "slug": {"required": False, "allow_null": True}
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # During nested parent validation, existing media may be omitted for updates.
        # Final validation is enforced in _upsert_interactives with resolved instance context.
        self.fields["interactives"].child.context["allow_missing_media_for_upsert"] = True

    def validate(self, attrs):
        # Frontend editor controls interactive key placement in content.
        return attrs
    def _get_file_from_request(self, files, index, field):
        """
        Accept multiple multipart naming conventions for nested fields.
        Examples handled:
          interactives[0][image_upload]
          interactives[0].image_upload
          interactives[0]image_upload
          interactive_files[0][image] (legacy)
        """
        candidates = (
            f"interactives[{index}][{field}]",
            f"interactives[{index}].{field}",
            f"interactives[{index}]{field}",
        )
        for key in candidates:
            f = files.get(key)
            if f:
                return f
        # legacy fallback keys
        legacy_map = {
            "image_upload": f"interactive_files[{index}][image]",
            "audio_upload": f"interactive_files[{index}][audio]",
            "video_upload": f"interactive_files[{index}][video]",
        }
        legacy_key = legacy_map.get(field)
        if legacy_key:
            return files.get(legacy_key)
        return None
    def _hydrate_interactive_files(self, interactives_data):
        """
        Merge uploaded files from request.FILES into each interactive payload
        before child serializer validation.
        """
        if not interactives_data:
            return interactives_data
        request = self.context.get("request")
        if not request:
            return interactives_data
        files = request.FILES
        for index, payload in enumerate(interactives_data):
            image_file = self._get_file_from_request(files, index, "image_upload")
            audio_file = self._get_file_from_request(files, index, "audio_upload")
            video_file = self._get_file_from_request(files, index, "video_upload")
            if image_file:
                payload["image_upload"] = image_file
            if audio_file:
                payload["audio_upload"] = audio_file
            if video_file:
                payload["video_upload"] = video_file
        return interactives_data
    @transaction.atomic
    def create(self, validated_data):
        interactives_data = validated_data.pop("interactives", [])
        interactives_data = self._hydrate_interactive_files(interactives_data)
        sections_data = validated_data.pop("sections", [])
        request = self.context.get("request")
        created_by = validated_data.pop("created_by", getattr(request, "user", None))
        article = Article.objects.create(created_by=created_by, **validated_data)
        self._upsert_interactives(article, interactives_data)
        self._replace_sections(article, sections_data)
        return article
    @transaction.atomic
    def update(self, instance, validated_data):
        interactives_data = validated_data.pop("interactives", None)
        if interactives_data is not None:
            interactives_data = self._hydrate_interactive_files(interactives_data)
        sections_data = validated_data.pop("sections", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if interactives_data is not None:
            self._upsert_interactives(instance, interactives_data, replace=True)
        if sections_data is not None:
            self._replace_sections(instance, sections_data)
        return instance
    def _upsert_interactives(self, article, interactives_data, replace=False):
        existing = {item.id: item for item in article.interactives.all()}
        existing_by_key = {item.key: item for item in article.interactives.all()}
        retained_ids = set()

        for payload in interactives_data:
            payload = dict(payload or {})

            # 1) Skip malformed empty rows from multipart parsing
            if not payload:
                continue

            interactive_id = payload.pop("id", None)
            interactive_key = payload.get("key")

            # 2) Normalize id from string
            if isinstance(interactive_id, str) and interactive_id.isdigit():
                interactive_id = int(interactive_id)

            # 3) Resolve existing instance by id, then by key
            instance = existing.get(interactive_id) if interactive_id is not None else None
            if instance is None and interactive_key:
                instance = existing_by_key.get(interactive_key)

            serializer = InteractiveElementSerializer(
                instance=instance,
                data=payload,
                partial=instance is not None,
                context={**self.context, "article": article},
            )
            serializer.is_valid(raise_exception=True)
            interactive = serializer.save(article=article)
            retained_ids.add(interactive.id)

        if replace:
            article.interactives.exclude(id__in=retained_ids).delete()
    def _replace_sections(self, article, sections_data):
        article.sections.all().delete()
        for payload in sections_data:
            payload.pop("article", None)
        section_instances = [ExpandableSection(article=article, **payload) for payload in sections_data]
        if section_instances:
            ExpandableSection.objects.bulk_create(section_instances)