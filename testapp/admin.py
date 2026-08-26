from django.contrib import admin

from .models import Commune, Observation


@admin.register(Commune)
class CommuneAdmin(admin.ModelAdmin):
    list_display = ("nom", "code_insee", "has_geometry")
    search_fields = ("nom", "code_insee")

    @admin.display(boolean=True, description="géométrie")
    def has_geometry(self, commune):
        return commune.geom is not None


@admin.register(Observation)
class ObservationAdmin(admin.ModelAdmin):
    list_display = ("espece", "commune", "date_observation", "effectif")
    list_filter = ("date_observation", "commune")
    search_fields = ("espece", "commune__nom")
