from django.http import FileResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from djangogeoexporter import ExportError, MissingDependencyError, export

from .exports import ObservationsExport
from .forms import ExportConfigurationForm
from .models import Commune, Observation


class ExportFileResponse(FileResponse):
    def __init__(self, result):
        self.export_result = result
        super().__init__(
            result.file,
            as_attachment=True,
            filename=result.filename,
            content_type=result.content_type,
        )

    def close(self):
        try:
            super().close()
        finally:
            self.export_result.cleanup()


def _form_context(form):
    return {
        "form": form,
        "communes_count": Commune.objects.count(),
        "observations_count": Observation.objects.count(),
    }


@require_GET
def index(request):
    return render(
        request,
        "testapp/export_form.html",
        _form_context(ExportConfigurationForm()),
    )


@require_GET
def download_export(request):
    form = ExportConfigurationForm(request.GET)
    if not form.is_valid():
        return render(
            request,
            "testapp/export_form.html",
            _form_context(form),
            status=400,
        )
    try:
        result = export(
            ObservationsExport,
            format=form.cleaned_data["format"],
            context=form.cleaned_data,
        )
    except (ExportError, MissingDependencyError) as error:
        return JsonResponse({"error": str(error)}, status=400)
    return ExportFileResponse(result)
