from __future__ import annotations

from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=255, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self) -> str:
        return str(self.name)

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or "cat-%s" % (getattr(self, "pk", "new"))
            self.slug = base
            n = 0
            while Category.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                n += 1
                self.slug = "%s-%d" % (base, n)
        super().save(*args, **kwargs)


class Tag(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return str(self.name)


class Post(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    link = models.URLField(blank=True)
    featured_image = models.ImageField(upload_to="posts/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    category = models.ForeignKey(
        Category,
        verbose_name="Categories",
        on_delete=models.PROTECT,
        related_name="posts",
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="posts")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return str(self.title)
