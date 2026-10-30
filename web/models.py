from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from typing import override

from django.db import models, transaction
from django.db.models import Q
from django.db.models.base import ModelBase
from django.urls import reverse
from django.utils.text import slugify

NEWS_CATEGORY_NAME = "news"

# Field annotations spell out the (set, get) types that django-stubs cannot
# infer without its mypy plugin, so type checkers see e.g. `str`, not Unknown.


class Category(models.Model):
    id: models.BigAutoField[int, int] = models.BigAutoField(
        primary_key=True, verbose_name="ID"
    )
    name: models.CharField[str, str] = models.CharField(max_length=255)
    slug: models.SlugField[str, str] = models.SlugField(
        unique=True, max_length=255, blank=True
    )

    class Meta:
        ordering: list[str] = ["name"]
        verbose_name: str = "Category"
        verbose_name_plural: str = "Categories"

    @override
    def __str__(self) -> str:
        return self.name

    @property
    def is_news(self) -> bool:
        """News sections use the featured (image-led) layout instead of a list."""
        return self.name.strip().lower() == NEWS_CATEGORY_NAME

    @override
    def save(
        self,
        *,
        force_insert: bool | tuple[ModelBase, ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        if not self.slug:
            base = slugify(self.name) or f"cat-{self.id or 'new'}"
            self.slug = base
            n = 0
            while Category.objects.filter(slug=self.slug).exclude(pk=self.id).exists():
                n += 1
                self.slug = f"{base}-{n}"
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )


class Tag(models.Model):
    id: models.BigAutoField[int, int] = models.BigAutoField(
        primary_key=True, verbose_name="ID"
    )
    name: models.CharField[str, str] = models.CharField(max_length=255)

    class Meta:
        ordering: list[str] = ["name"]

    @override
    def __str__(self) -> str:
        return self.name


class Issue(models.Model):
    """A monthly issue of the newsletter. Exactly one issue is shown on the home page."""

    id: models.BigAutoField[int, int] = models.BigAutoField(
        primary_key=True, verbose_name="ID"
    )
    number: models.PositiveIntegerField[int, int] = models.PositiveIntegerField(
        unique=True
    )
    published_on: models.DateField[date, date] = models.DateField()
    subject: models.CharField[str, str] = models.CharField(
        max_length=255,
        blank=True,
        help_text="Subject line of the email send, shown in the issue archive.",
    )
    is_active: models.BooleanField[bool, bool] = models.BooleanField(
        default=False,
        help_text=(
            "The active issue is the one shown on the home page. Activating an issue deactivates the others."
        ),
    )

    class Meta:
        ordering: list[str] = ["-number"]
        constraints: list[models.BaseConstraint] = [
            models.UniqueConstraint(
                fields=["is_active"],
                condition=Q(is_active=True),
                name="web_issue_single_active",
            ),
        ]

    @override
    def __str__(self) -> str:
        return f"#{self.number:03d}"

    def get_absolute_url(self) -> str:
        # The active issue lives at the site root; archived ones have their own page.
        if self.is_active:
            return reverse("web:home")
        return reverse("web:issue", kwargs={"number": self.number})

    @override
    def save(
        self,
        *,
        force_insert: bool | tuple[ModelBase, ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        # Deactivate the previous active issue in the same transaction, so the
        # unique constraint never sees two active rows.
        with transaction.atomic(using=using):
            if self.is_active:
                _ = (
                    Issue.objects.filter(is_active=True)
                    .exclude(pk=self.id)
                    .update(is_active=False)
                )
            super().save(
                force_insert=force_insert,
                force_update=force_update,
                using=using,
                update_fields=update_fields,
            )

    def activate(self) -> None:
        self.is_active = True
        self.save(update_fields=["is_active"])


class Post(models.Model):
    id: models.BigAutoField[int, int] = models.BigAutoField(
        primary_key=True, verbose_name="ID"
    )
    title: models.CharField[str, str] = models.CharField(max_length=255)
    description: models.TextField[str, str] = models.TextField(blank=True)
    link: models.URLField[str, str] = models.URLField(blank=True)
    featured_image: models.ImageField = models.ImageField(
        upload_to="posts/", blank=True, null=True
    )
    created_at: models.DateTimeField[datetime, datetime] = models.DateTimeField(
        auto_now_add=True
    )
    category: models.ForeignKey[Category, Category] = models.ForeignKey(
        Category,
        verbose_name="Categories",
        on_delete=models.PROTECT,
        related_name="posts",
    )
    tags: models.ManyToManyField[Tag, models.Model] = models.ManyToManyField(
        Tag, blank=True, related_name="posts"
    )
    issue: models.ForeignKey[Issue, Issue] = models.ForeignKey(
        Issue,
        on_delete=models.PROTECT,
        related_name="posts",
    )

    class Meta:
        ordering: list[str] = ["-created_at"]

    @override
    def __str__(self) -> str:
        return self.title
