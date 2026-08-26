import django.contrib.gis.db.models.fields
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("testapp", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="commune",
            name="geom",
            field=django.contrib.gis.db.models.fields.MultiPolygonField(
                blank=True,
                null=True,
                srid=4326,
                verbose_name="géométrie",
            ),
        ),
    ]
