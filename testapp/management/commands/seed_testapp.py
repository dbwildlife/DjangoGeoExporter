from datetime import date

from django.contrib.gis.geos import MultiPolygon, Polygon
from django.core.management.base import BaseCommand

from testapp.models import Commune, Observation


class Command(BaseCommand):
    help = "Crée un petit jeu de données pour tester les exports."

    def handle(self, *args, **options):
        paris, _ = Commune.objects.update_or_create(
            code_insee="75056",
            defaults={
                "nom": "Paris",
                "geom": MultiPolygon(
                    Polygon.from_bbox((2.2241, 48.8156, 2.4699, 48.9022)),
                    srid=4326,
                ),
            },
        )
        lyon, _ = Commune.objects.update_or_create(
            code_insee="69123",
            defaults={
                "nom": "Lyon",
                "geom": MultiPolygon(
                    Polygon.from_bbox((4.7718, 45.7074, 4.8984, 45.8083)),
                    srid=4326,
                ),
            },
        )

        samples = (
            (paris, "Pipistrelle commune", date(2026, 6, 12), 4),
            (paris, "Noctule commune", date(2026, 6, 13), 1),
            (lyon, "Grand rhinolophe", date(2026, 7, 2), 2),
        )
        for commune, espece, observed_on, count in samples:
            Observation.objects.get_or_create(
                commune=commune,
                espece=espece,
                date_observation=observed_on,
                defaults={"effectif": count},
            )

        self.stdout.write(self.style.SUCCESS("Données de test créées."))
