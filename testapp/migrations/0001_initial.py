import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Commune",
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
                (
                    "nom",
                    models.CharField(
                        max_length=100, unique=True, verbose_name="nom"
                    ),
                ),
                (
                    "code_insee",
                    models.CharField(
                        max_length=5, unique=True, verbose_name="code INSEE"
                    ),
                ),
            ],
            options={"ordering": ("nom",)},
        ),
        migrations.CreateModel(
            name="Observation",
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
                (
                    "espece",
                    models.CharField(max_length=150, verbose_name="espèce"),
                ),
                (
                    "date_observation",
                    models.DateField(verbose_name="date d'observation"),
                ),
                (
                    "effectif",
                    models.PositiveIntegerField(
                        default=1, verbose_name="effectif"
                    ),
                ),
                (
                    "commune",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="observations",
                        to="testapp.commune",
                        verbose_name="commune",
                    ),
                ),
            ],
            options={"ordering": ("date_observation", "espece")},
        ),
    ]
