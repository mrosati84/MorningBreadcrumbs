# Backfill: every post that existed before issues were introduced belongs to
# issue #1, which becomes the active issue. Does nothing on an empty database.

from django.db import migrations
from django.db.models import Min


def assign_first_issue(apps, schema_editor):
    Issue = apps.get_model("web", "Issue")
    Post = apps.get_model("web", "Post")

    orphans = Post.objects.filter(issue__isnull=True)
    first_post_at = orphans.aggregate(first=Min("created_at"))["first"]
    if first_post_at is None:
        return

    issue, _ = Issue.objects.get_or_create(
        number=1,
        defaults={"published_on": first_post_at.date(), "is_active": True},
    )
    orphans.update(issue=issue)


def unassign_first_issue(apps, schema_editor):
    Issue = apps.get_model("web", "Issue")
    Post = apps.get_model("web", "Post")

    Post.objects.filter(issue__number=1).update(issue=None)
    Issue.objects.filter(number=1).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("web", "0006_issue_post_issue"),
    ]

    operations = [
        migrations.RunPython(assign_first_issue, unassign_first_issue),
    ]
