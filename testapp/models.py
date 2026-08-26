from django.contrib.gis.db import models


class Commune(models.Model):
    nom = models.CharField("nom", max_length=100, unique=True)
    code_insee = models.CharField("code INSEE", max_length=5, unique=True)
    geom = models.MultiPolygonField(
        "géométrie",
        srid=4326,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ("nom",)

    def __str__(self):
        return f"{self.nom} ({self.code_insee})"


class Observation(models.Model):
    commune = models.ForeignKey(
        Commune,
        verbose_name="commune",
        related_name="observations",
        on_delete=models.CASCADE,
    )
    espece = models.CharField("espèce", max_length=150)
    date_observation = models.DateField("date d'observation")
    effectif = models.PositiveIntegerField("effectif", default=1)

    class Meta:
        ordering = ("date_observation", "espece")

    def __str__(self):
        return f"{self.espece} — {self.commune.nom}"
