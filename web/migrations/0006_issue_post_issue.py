# Adds the Issue model. Post.issue starts nullable so existing posts can be
# backfilled by 0007 before 0008 makes the column required.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("web", "0005_enable_pg_trgm"),
    ]

    operations = [
        migrations.CreateModel(
            name="Issue",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("number", models.PositiveIntegerField(unique=True)),
                ("published_on", models.DateField()),
                (
                    "subject",
                    models.CharField(
                        blank=True,
                        help_text="Subject line of the email send, shown in the issue archive.",
                        max_length=255,
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=False,
                        help_text="The active issue is the one shown on the home page. "
                        "Activating an issue deactivates the others.",
                    ),
                ),
            ],
            options={
                "ordering": ["-number"],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("is_active", True)),
                        fields=("is_active",),
                        name="web_issue_single_active",
                    )
                ],
            },
        ),
        migrations.AddField(
            model_name="post",
            name="issue",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="posts",
                to="web.issue",
            ),
        ),
    ]
