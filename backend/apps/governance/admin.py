from django.contrib import admin

from .models import ApprovalRecord, DataSource


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "organisation", "responsible_person", "collection_start", "collection_end")
    search_fields = ("name", "organisation")


@admin.register(ApprovalRecord)
class ApprovalRecordAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "content_type", "object_id", "action", "from_status", "to_status", "actor")
    list_filter = ("action", "content_type")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
