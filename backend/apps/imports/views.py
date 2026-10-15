from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import require
from apps.accounts.roles import Capability, has_capability
from apps.governance.models import DataSource

from . import services, templates
from .base import REGISTRY, get_importer
from .models import ImportBatch, ImportRow


# ---------- serializers ----------
class ColumnSerializer(serializers.Serializer):
    key = serializers.CharField()
    header = serializers.CharField()
    required = serializers.BooleanField()
    kind = serializers.CharField()
    help = serializers.CharField()
    example = serializers.CharField()
    choices = serializers.SerializerMethodField()

    def get_choices(self, col) -> list[str] | None:
        return col.choices() if col.choices else None


class ImporterSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    description = serializers.CharField()
    columns = ColumnSerializer(many=True)


class ImportRowSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = ImportRow
        fields = ["id", "row_number", "status", "status_label", "action", "raw", "values",
                  "errors", "warnings", "target_id", "corrected"]


class ImportBatchSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    importer_label = serializers.SerializerMethodField()
    counts = serializers.SerializerMethodField()
    uploaded_by = serializers.CharField(source="uploaded_by.username", default="", read_only=True)
    committed_by = serializers.CharField(source="committed_by.username", default="", read_only=True)
    data_source = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ImportBatch
        fields = ["id", "importer", "importer_label", "original_filename", "status", "status_label",
                  "data_source", "file_warnings", "counts", "uploaded_by", "uploaded_at",
                  "committed_by", "committed_at"]

    def get_importer_label(self, obj) -> str:
        imp = get_importer(obj.importer)
        return imp.label if imp else obj.importer

    def get_counts(self, obj) -> dict:
        return obj.counts()


class UploadSerializer(serializers.Serializer):
    importer = serializers.ChoiceField(choices=[])
    file = serializers.FileField()
    data_source = serializers.PrimaryKeyRelatedField(queryset=DataSource.objects.all(), required=False,
                                                     allow_null=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["importer"].choices = list(REGISTRY)


class CorrectRowSerializer(serializers.Serializer):
    raw = serializers.DictField(help_text="Corrected values keyed by column key; other columns are kept.")


class CommitSerializer(serializers.Serializer):
    skip_problem_rows = serializers.BooleanField(default=False,
                                                 help_text="Confirm that rows with problems are left out.")


# ---------- views ----------
def _importers_for(user):
    return [imp for imp in REGISTRY.values() if has_capability(user, imp.capability)]


def _importer_or_403(user, key):
    imp = get_importer(key)
    if imp is None or not has_capability(user, imp.capability):
        return None
    return imp


class ImporterListView(APIView):
    """Kinds of data this user may upload, with their columns."""

    permission_classes = [require(Capability.ENTER_DATA)]

    @extend_schema(responses=ImporterSerializer(many=True))
    def get(self, request):
        return Response(ImporterSerializer(_importers_for(request.user), many=True).data)


class TemplateView(APIView):
    """Download the upload template (Excel by default, or ?file_type=csv)."""

    permission_classes = [require(Capability.ENTER_DATA)]

    @extend_schema(parameters=[OpenApiParameter("file_type", str, enum=["xlsx", "csv"])],
                   responses={(200, "application/octet-stream"): bytes})
    def get(self, request, key):
        imp = _importer_or_403(request.user, key)
        if imp is None:
            return Response({"detail": "Template not found."}, status=status.HTTP_404_NOT_FOUND)
        if request.query_params.get("file_type") == "csv":
            body, ctype, ext = templates.build_csv(imp), "text/csv; charset=utf-8", "csv"
        else:
            body = templates.build_xlsx(imp)
            ctype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ext = "xlsx"
        resp = HttpResponse(body, content_type=ctype)
        resp["Content-Disposition"] = f'attachment; filename="blue-bayelsa-{imp.key}-template.{ext}"'
        return resp


class ImportBatchViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Upload a file, review and correct rows, then import or cancel."""

    permission_classes = [require(Capability.ENTER_DATA)]
    serializer_class = ImportBatchSerializer
    filterset_fields = ["importer", "status"]

    def get_queryset(self):
        keys = [imp.key for imp in _importers_for(self.request.user)]
        return ImportBatch.objects.filter(importer__in=keys).select_related("uploaded_by", "committed_by")

    def _fail(self, message, code=status.HTTP_400_BAD_REQUEST):
        return Response({"detail": message}, status=code)

    @extend_schema(request={"multipart/form-data": UploadSerializer}, responses=ImportBatchSerializer)
    def create(self, request):
        ser = UploadSerializer(data=request.data)
        if not ser.is_valid():
            messages = [str(m) for msgs in ser.errors.values() for m in msgs]
            return Response({"detail": " ".join(messages), "errors": ser.errors},
                            status=status.HTTP_400_BAD_REQUEST)
        imp = _importer_or_403(request.user, ser.validated_data["importer"])
        if imp is None:
            return self._fail("You do not have permission to upload this kind of data.", status.HTTP_403_FORBIDDEN)
        try:
            batch = services.stage_upload(imp, ser.validated_data["file"], user=request.user,
                                          data_source=ser.validated_data.get("data_source"), request=request)
        except services.BatchError as e:
            return self._fail(str(e))
        return Response(ImportBatchSerializer(batch).data, status=status.HTTP_201_CREATED)

    def get_parsers(self):
        if getattr(self, "action", None) == "create":
            return [MultiPartParser(), FormParser()]
        return super().get_parsers()

    @extend_schema(parameters=[OpenApiParameter("status", str, enum=ImportRow.Status.values)],
                   responses=ImportRowSerializer(many=True))
    @action(detail=True, methods=["get"])
    def rows(self, request, pk=None):
        batch = self.get_object()
        qs = batch.rows.all()
        if request.query_params.get("status"):
            qs = qs.filter(status=request.query_params["status"])
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(ImportRowSerializer(page, many=True).data)

    def _row(self, batch, row_id):
        return get_object_or_404(ImportRow, batch=batch, pk=row_id)

    @extend_schema(request=CorrectRowSerializer, responses=ImportRowSerializer)
    @action(detail=True, methods=["patch"], url_path=r"rows/(?P<row_id>\d+)")
    def correct_row(self, request, pk=None, row_id=None):
        batch = self.get_object()
        ser = CorrectRowSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            row = services.correct_row(get_importer(batch.importer), self._row(batch, row_id),
                                       ser.validated_data["raw"], user=request.user)
        except services.BatchError as e:
            return self._fail(str(e))
        return Response(ImportRowSerializer(row).data)

    @extend_schema(request=None, responses=ImportRowSerializer)
    @action(detail=True, methods=["post"], url_path=r"rows/(?P<row_id>\d+)/skip")
    def skip_row(self, request, pk=None, row_id=None):
        return self._skip(request, pk, row_id, True)

    @extend_schema(request=None, responses=ImportRowSerializer)
    @action(detail=True, methods=["post"], url_path=r"rows/(?P<row_id>\d+)/unskip")
    def unskip_row(self, request, pk=None, row_id=None):
        return self._skip(request, pk, row_id, False)

    def _skip(self, request, pk, row_id, skip):
        batch = self.get_object()
        try:
            row = services.skip_row(get_importer(batch.importer), self._row(batch, row_id),
                                    user=request.user, skip=skip)
        except services.BatchError as e:
            return self._fail(str(e))
        return Response(ImportRowSerializer(row).data)

    @extend_schema(request=CommitSerializer, responses=ImportBatchSerializer)
    @action(detail=True, methods=["post"])
    def commit(self, request, pk=None):
        batch = self.get_object()
        ser = CommitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            batch = services.commit_batch(get_importer(batch.importer), batch, user=request.user,
                                          skip_problem_rows=ser.validated_data["skip_problem_rows"],
                                          request=request)
        except services.BatchError as e:
            return self._fail(str(e))
        return Response(ImportBatchSerializer(batch).data)

    @extend_schema(request=None, responses=ImportBatchSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        batch = self.get_object()
        try:
            batch = services.cancel_batch(batch, user=request.user, request=request)
        except services.BatchError as e:
            return self._fail(str(e))
        return Response(ImportBatchSerializer(batch).data)
