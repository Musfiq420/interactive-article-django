import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

from .validators import (
    AUDIO_EXTENSIONS,
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS,
    validate_file_extension,
    validate_interactive_payload,
    validate_youtube_url,
)


class Article(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255, db_index=True)
    content = models.JSONField(
        null=True, blank=True,
        default=dict,  
        help_text="JSON representation of the rich text editor content."
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="articles",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


class InteractiveElement(models.Model):
    TYPE_IMAGE = "image"
    TYPE_AUDIO = "audio"
    TYPE_VIDEO = "video"
    TYPE_YOUTUBE = "youtube"
    TYPE_TEXT = "text"

    TYPE_CHOICES = (
        (TYPE_IMAGE, "Image"),
        (TYPE_AUDIO, "Audio"),
        (TYPE_VIDEO, "Video"),
        (TYPE_YOUTUBE, "YouTube"),
        (TYPE_TEXT, "Text"),
    )

    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="interactives",
    )
    key = models.CharField(max_length=100, db_index=True)
    display_text = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    image = models.ImageField(upload_to="interactive/images/", blank=True, null=True)
    audio = models.FileField(upload_to="interactive/audio/", blank=True, null=True)
    video = models.FileField(upload_to="interactive/videos/", blank=True, null=True)
    youtube_url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)
        constraints = [
            models.UniqueConstraint(fields=("article", "key"), name="unique_article_key"),
        ]

    def __str__(self) -> str:
        return f"{self.article.title}: {self.key}"

    def clean(self):
        validate_file_extension(self.image, IMAGE_EXTENSIONS, "Image")
        validate_file_extension(self.audio, AUDIO_EXTENSIONS, "Audio")
        validate_file_extension(self.video, VIDEO_EXTENSIONS, "Video")
        validate_youtube_url(self.youtube_url)
        validate_interactive_payload(
            self.type,
            {
                "image": self.image,
                "audio": self.audio,
                "video": self.video,
                "youtube_url": self.youtube_url,
                "description": self.description,
                "metadata": self.metadata,
            },
        )


class ExpandableSection(models.Model):
    article = models.ForeignKey(
        Article,
        on_delete=models.CASCADE,
        related_name="sections",
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("order", "id")

    def __str__(self) -> str:
        return f"{self.article.title}: {self.title}"
