from __future__ import annotations

import tempfile
from datetime import date, datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import ClassVar, cast, override

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.state import StateApps
from django.db.models.fields.files import ImageFieldFile
from django.db.models import Manager, Model
from django.test import TestCase, TransactionTestCase, override_settings
from PIL import Image
from django.urls import NoReverseMatch, reverse

from web.models import Category, Issue, Post
from web.views import Section, Tab


def create_post(issue: Issue, category: Category, title: str, link: str = "") -> None:
    _ = Post.objects.create(issue=issue, category=category, title=title, link=link)


class IssueModelTests(TestCase):
    def test_activating_an_issue_deactivates_the_previous_one(self) -> None:
        first = Issue.objects.create(
            number=1, published_on=date(2026, 9, 1), is_active=True
        )
        second = Issue.objects.create(number=2, published_on=date(2026, 10, 1))

        second.activate()

        first.refresh_from_db()
        self.assertFalse(first.is_active)
        self.assertTrue(Issue.objects.get(pk=second.id).is_active)

    def test_database_rejects_two_active_issues(self) -> None:
        _ = Issue.objects.create(
            number=1, published_on=date(2026, 9, 1), is_active=True
        )
        # Bypass Issue.save(), which would deactivate the first one.
        with self.assertRaises(IntegrityError), transaction.atomic():
            _ = Issue.objects.bulk_create(
                [Issue(number=2, published_on=date(2026, 10, 1), is_active=True)]
            )

    def test_absolute_url_points_active_issue_to_home(self) -> None:
        active = Issue.objects.create(
            number=2, published_on=date(2026, 10, 1), is_active=True
        )
        archived = Issue.objects.create(number=1, published_on=date(2026, 9, 1))

        self.assertEqual(active.get_absolute_url(), reverse("web:home"))
        self.assertEqual(archived.get_absolute_url(), reverse("web:issue", args=[1]))

    def test_news_category_is_matched_case_insensitively(self) -> None:
        self.assertTrue(Category(name="News").is_news)
        self.assertTrue(Category(name="news").is_news)
        self.assertFalse(Category(name="Newsletter").is_news)


class IssuePageTests(TestCase):
    old: ClassVar[Issue]
    current: ClassVar[Issue]
    news: ClassVar[Category]
    design: ClassVar[Category]

    @classmethod
    @override
    def setUpTestData(cls) -> None:
        cls.old = Issue.objects.create(number=1, published_on=date(2026, 9, 1))
        cls.current = Issue.objects.create(
            number=2, published_on=date(2026, 10, 1), is_active=True
        )
        cls.news = Category.objects.create(name="News")
        cls.design = Category.objects.create(name="Design")
        create_post(cls.current, cls.news, "Current lead", link="https://example.com/a")
        create_post(cls.current, cls.design, "Current design post")
        create_post(cls.old, cls.design, "Archived design post")

    def test_home_shows_only_the_active_issue(self) -> None:
        response = self.client.get(reverse("web:home"))

        self.assertContains(response, "Current lead")
        self.assertContains(response, "Current design post")
        self.assertNotContains(response, "Archived design post")
        self.assertContains(response, "#002")

    def test_no_template_syntax_leaks_into_the_page(self) -> None:
        # Django's {# #} comments are single-line: a multi-line one renders as text.
        response = self.client.get(reverse("web:home"))

        for marker in ("{#", "#}", "{%", "%}", "{{", "}}"):
            self.assertNotContains(response, marker)

    def test_news_section_comes_first_with_featured_layout(self) -> None:
        response = self.client.get(reverse("web:home"))

        sections = cast(list[Section], response.context["sections"])
        self.assertEqual([s.category.name for s in sections], ["News", "Design"])
        self.assertContains(response, 'class="lead"')

    def test_cards_show_creation_date(self) -> None:
        post = Post.objects.get(title="Current design post")
        response = self.client.get(reverse("web:home"))

        self.assertContains(response, post.created_at.strftime("%d.%m.%Y"))

    def test_category_filter_limits_sections(self) -> None:
        response = self.client.get(reverse("web:home"), {"c": self.design.slug})

        self.assertContains(response, "Current design post")
        self.assertNotContains(response, "Current lead")

    def test_unknown_category_is_404(self) -> None:
        response = self.client.get(reverse("web:home"), {"c": "missing"})

        self.assertEqual(response.status_code, 404)

    def test_archived_issue_page(self) -> None:
        response = self.client.get(reverse("web:issue", args=[1]))

        self.assertContains(response, "Archived design post")
        self.assertNotContains(response, "Current design post")
        self.assertContains(response, "Viewing issue #001")

    def test_active_issue_url_redirects_home(self) -> None:
        response = self.client.get(reverse("web:issue", args=[2]), {"c": "design"})

        self.assertRedirects(response, reverse("web:home") + "?c=design")

    def test_archive_overlay_lists_every_issue(self) -> None:
        response = self.client.get(reverse("web:home"))

        self.assertContains(response, 'href="/issues/1/"')
        self.assertContains(response, "Latest")

    def test_logo_links_home_in_header_and_issue_archive(self) -> None:
        response = self.client.get(reverse("web:issue", args=[1]))

        self.assertContains(
            response, f'<a href="{reverse("web:home")}" class="masthead__home"', count=2
        )

    def test_home_without_issues_renders_empty_state(self) -> None:
        _ = Post.objects.all().delete()
        _ = Issue.objects.all().delete()

        response = self.client.get(reverse("web:home"))

        self.assertContains(response, "Nothing filed here yet.")


class AllTabPreviewTests(TestCase):
    news: ClassVar[Category]
    design: ClassVar[Category]

    @classmethod
    @override
    def setUpTestData(cls) -> None:
        issue = Issue.objects.create(
            number=1, published_on=date(2026, 10, 1), is_active=True
        )
        cls.news = Category.objects.create(name="News")
        cls.design = Category.objects.create(name="Design")
        for n in range(5):
            create_post(issue, cls.news, f"News {n}")
        for n in range(6):
            create_post(issue, cls.design, f"Design {n}")

    def sections(self, **params: str) -> dict[str, Section]:
        response = self.client.get(reverse("web:home"), params)
        sections = cast(list[Section], response.context["sections"])
        return {section.category.name: section for section in sections}

    def test_all_tab_shows_three_news_and_four_per_category(self) -> None:
        sections = self.sections()

        self.assertEqual(len(sections["News"].posts), 3)
        self.assertEqual(len(sections["Design"].posts), 4)
        # Section headers still count every entry of the category.
        self.assertEqual(sections["News"].total, 5)
        self.assertEqual(sections["Design"].total, 6)

    def test_previews_show_the_most_recent_posts(self) -> None:
        shown = [post.title for post in self.sections()["Design"].posts]

        self.assertEqual(shown, ["Design 5", "Design 4", "Design 3", "Design 2"])

    def test_tab_counts_are_not_limited(self) -> None:
        response = self.client.get(reverse("web:home"))
        counts = {
            tab.label: tab.count for tab in cast(list[Tab], response.context["tabs"])
        }

        self.assertEqual(counts, {"All": 11, "News": 5, "Design": 6})

    def test_category_tab_shows_every_entry(self) -> None:
        self.assertEqual(len(self.sections(c=self.news.slug)["News"].posts), 5)
        self.assertEqual(len(self.sections(c=self.design.slug)["Design"].posts), 6)


class SearchTests(TestCase):
    @classmethod
    @override
    def setUpTestData(cls) -> None:
        old = Issue.objects.create(number=1, published_on=date(2026, 9, 1))
        current = Issue.objects.create(
            number=2, published_on=date(2026, 10, 1), is_active=True
        )
        category = Category.objects.create(name="Tools")
        create_post(old, category, "Typography toolkit")
        create_post(current, category, "Typography toolkit, revisited")

    def test_search_spans_all_issues_and_shows_each_issue(self) -> None:
        response = self.client.get(reverse("web:search"), {"q": "typography toolkit"})

        results = cast(list[Post], response.context["results"])
        self.assertEqual({post.issue.number for post in results}, {1, 2})
        self.assertContains(
            response, '<span class="row__marker">#001</span>', html=False
        )
        self.assertContains(
            response, '<span class="row__marker">#002</span>', html=False
        )
        self.assertContains(response, "[ Tools ]")

    def test_empty_query_redirects_home(self) -> None:
        response = self.client.get(reverse("web:search"), {"q": "  "})

        self.assertRedirects(response, reverse("web:home"))

    def test_no_results(self) -> None:
        response = self.client.get(reverse("web:search"), {"q": "qqqqzzzz"})

        self.assertContains(response, "00 results")


class FeaturedImageOptimizationTests(TestCase):
    def test_upload_is_resized_to_webp_without_leftover_files(self) -> None:
        buffer = BytesIO()
        Image.new("RGB", (3200, 1600), "orange").save(buffer, "JPEG")
        upload = SimpleUploadedFile("photo.jpg", buffer.getvalue(), "image/jpeg")
        issue = Issue.objects.create(number=1, published_on=date(2026, 9, 1))
        category = Category.objects.create(name="News")

        with (
            tempfile.TemporaryDirectory() as media_root,
            override_settings(MEDIA_ROOT=media_root),
        ):
            post = Post.objects.create(
                issue=issue, category=category, title="Photo", featured_image=upload
            )

            post.refresh_from_db()
            image = cast(ImageFieldFile, post.featured_image)
            self.assertEqual(image.name, "posts/photo.webp")
            files = sorted(p.name for p in (Path(media_root) / "posts").iterdir())
            self.assertEqual(files, ["photo.webp"])
            with Image.open(Path(media_root) / "posts" / "photo.webp") as optimized:
                self.assertEqual(optimized.size, (1600, 800))


class LoginRemovedTests(TestCase):
    def test_login_routes_are_gone(self) -> None:
        for name in ("login", "logout"):
            with self.assertRaises(NoReverseMatch):
                _ = reverse(name)
        self.assertEqual(self.client.get("/accounts/login/").status_code, 404)


class AssignFirstIssueMigrationTests(TransactionTestCase):
    """Posts created before issues existed end up in issue #1."""

    before: ClassVar[list[tuple[str, str]]] = [("web", "0005_enable_pg_trgm")]
    after: ClassVar[list[tuple[str, str]]] = [("web", "0008_alter_post_issue_required")]

    @override
    def tearDown(self) -> None:
        # Leave the schema fully migrated for the other tests.
        _ = call_command("migrate", verbosity=0)

    def migrate(self, targets: list[tuple[str, str]]) -> StateApps:
        """Migrate the test database to `targets`; return the historical models."""
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        _ = executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    @staticmethod
    def manager(apps: StateApps, model_name: str) -> Manager[Model]:
        return cast(Manager[Model], apps.get_model("web", model_name)._default_manager)

    def test_existing_posts_are_assigned_to_issue_one(self) -> None:
        old_apps = self.migrate(self.before)
        categories = self.manager(old_apps, "Category")
        posts = self.manager(old_apps, "Post")
        category = categories.create(name="Design", slug="design")
        for day in (12, 20):
            _ = posts.create(title=f"Post {day}", category=category)
            _ = posts.filter(title=f"Post {day}").update(
                created_at=datetime(2026, 9, day, 8, tzinfo=timezone.utc)
            )

        new_apps = self.migrate(self.after)
        issues = self.manager(new_apps, "Issue")
        posts = self.manager(new_apps, "Post")

        self.assertEqual(
            list(issues.values("number", "is_active", "published_on")),
            [{"number": 1, "is_active": True, "published_on": date(2026, 9, 12)}],
        )
        self.assertEqual(posts.filter(issue__number=1).count(), 2)

    def test_empty_database_gets_no_issue(self) -> None:
        _ = self.migrate(self.before)
        new_apps = self.migrate(self.after)

        self.assertFalse(self.manager(new_apps, "Issue").exists())
