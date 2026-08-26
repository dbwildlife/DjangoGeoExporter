from django import forms

from .models import Commune


class ExportConfigurationForm(forms.Form):
    format = forms.ChoiceField(
        label="Format",
        choices=(
            ("csv", "CSV"),
            ("tsv", "TSV"),
            ("xlsx", "Excel (.xlsx)"),
            ("ods", "OpenDocument (.ods)"),
            ("parquet", "GeoParquet / Parquet"),
            ("gpkg", "GeoPackage (.gpkg)"),
        ),
        initial="gpkg",
    )
    commune = forms.ModelChoiceField(
        label="Commune",
        queryset=Commune.objects.none(),
        required=False,
        empty_label="Toutes les communes",
    )
    date_debut = forms.DateField(
        label="Observations à partir du",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    date_fin = forms.DateField(
        label="Observations jusqu'au",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    inclure_communes = forms.BooleanField(
        label="Inclure la couche géographique des communes",
        required=False,
        initial=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["commune"].queryset = Commune.objects.order_by("nom")

    def clean(self):
        data = super().clean()
        if (
            data.get("date_debut")
            and data.get("date_fin")
            and data["date_debut"] > data["date_fin"]
        ):
            raise forms.ValidationError(
                "La date de début doit être antérieure à la date de fin."
            )
        return data
