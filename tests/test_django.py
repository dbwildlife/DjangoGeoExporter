import zipfile
from datetime import date
from io import BytesIO

import pytest
from django.contrib.gis.geos import MultiPolygon
from django.core.management import call_command
from django.urls import reverse

from testapp.forms import ExportConfigurationForm
from testapp.models import Commune, Observation

pytestmark = pytest.mark.django_db


@pytest.fixture
def sample_data():
    call_command("seed_testapp", verbosity=0)
    return {
        "paris": Commune.objects.get(code_insee="75056"),
        "lyon": Commune.objects.get(code_insee="69123"),
    }


def test_seed_command_creates_geographic_communes(sample_data):
    assert Commune.objects.count() == 2
    assert Observation.objects.count() == 3
    assert isinstance(sample_data["paris"].geom, MultiPolygon)
    assert sample_data["paris"].geom.srid == 4326
    assert sample_data["paris"].geom.valid


def test_export_form_page(client, sample_data):
    response = client.get(reverse("testapp:index"))

    assert response.status_code == 200
    assert b"Configurer" in response.content
    assert sample_data["paris"].nom.encode() in response.content


def test_form_rejects_an_inverted_date_range():
    form = ExportConfigurationForm(
        {"format": "csv", "date_debut": "2026-08-02", "date_fin": "2026-08-01"}
    )

    assert not form.is_valid()
    assert "date de début" in form.non_field_errors()[0]


def test_filtered_csv_export_without_commune_layer(client, sample_data):
    response = client.get(
        reverse("testapp:export"),
        {
            "format": "csv",
            "commune": sample_data["paris"].pk,
            "date_debut": date(2026, 6, 13).isoformat(),
        },
    )

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/csv")
    content = b"".join(response.streaming_content).decode("utf-8-sig")
    response.close()
    assert "Noctule commune" in content
    assert "Pipistrelle commune" not in content
    assert "Grand rhinolophe" not in content


def test_relational_csv_export_contains_both_tables(client, sample_data):
    response = client.get(
        reverse("testapp:export"),
        {"format": "csv", "inclure_communes": "on"},
    )

    assert response.status_code == 200
    archive_bytes = b"".join(response.streaming_content)
    response.close()

    with zipfile.ZipFile(BytesIO(archive_bytes)) as archive:
        assert set(archive.namelist()) == {"communes.csv", "observations.csv"}
        communes = archive.read("communes.csv").decode("utf-8-sig")
        assert "MULTIPOLYGON" in communes
