import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("web", "0007_assign_existing_posts_to_first_issue"),
    ]

    operations = [
        migrations.AlterField(
            model_name="post",
            name="issue",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="posts",
                to="web.issue",
            ),
        ),
        # Primary keys are now declared explicitly (for typing); no SQL change.
        migrations.AlterField(
            model_name="category",
            name="id",
            field=models.BigAutoField(
                primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.AlterField(
            model_name="issue",
            name="id",
            field=models.BigAutoField(
                primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.AlterField(
            model_name="post",
            name="id",
            field=models.BigAutoField(
                primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
        migrations.AlterField(
            model_name="tag",
            name="id",
            field=models.BigAutoField(
                primary_key=True, serialize=False, verbose_name="ID"
            ),
        ),
    ]
