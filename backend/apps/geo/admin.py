from django.contrib.gis import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import LGA, Activity, Community, Sector


@admin.register(LGA)
class LGAAdmin(admin.GISModelAdmin, SimpleHistoryAdmin):
    list_display = ("name", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Community)
class CommunityAdmin(admin.GISModelAdmin, SimpleHistoryAdmin):
    list_display = ("name", "lga", "is_survey_community", "is_active")
    list_filter = ("lga", "is_survey_community", "is_active")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Sector)
class SectorAdmin(SimpleHistoryAdmin):
    list_display = ("name", "display_order", "is_active")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Activity)
class ActivityAdmin(SimpleHistoryAdmin):
    list_display = ("name", "sector", "display_order", "is_active")
    list_filter = ("sector",)
    prepopulated_fields = {"slug": ("name",)}
