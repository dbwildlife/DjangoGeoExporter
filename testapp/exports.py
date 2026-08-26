from djangogeoexporter import ExportDefinition, ExportTable, Field

from .models import Commune, Observation


class ObservationsExport(ExportDefinition):
    name = "observations"

    @classmethod
    def get_tables(cls, context):
        communes = Commune.objects.all()
        observations = Observation.objects.select_related("commune").all()
        commune = context.get("commune")
        if commune:
            communes = communes.filter(pk=commune.pk)
            observations = observations.filter(commune=commune)
        if context.get("date_debut"):
            observations = observations.filter(
                date_observation__gte=context["date_debut"]
            )
        if context.get("date_fin"):
            observations = observations.filter(
                date_observation__lte=context["date_fin"]
            )

        commune_table = ExportTable(
            "communes",
            communes,
            ("id", "nom", "code_insee", "geom"),
            model=Commune,
            use_verbose_names=True,
            geometry_field="geom",
            crs="EPSG:4326",
        )
        observation_table = ExportTable(
            "observations",
            observations,
            (
                "id",
                Field("commune_id", source="commune_id", label="ID commune"),
                Field("commune", source="commune__nom"),
                "espece",
                "date_observation",
                "effectif",
            ),
            model=Observation,
            use_verbose_names=True,
        )
        return (
            (commune_table, observation_table)
            if context.get("inclure_communes", True)
            else (observation_table,)
        )
