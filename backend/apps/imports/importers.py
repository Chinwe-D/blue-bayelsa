"""
Concrete importers. Enterprises, indicator values and investment
opportunities will be added here in Phase 4, once the questionnaire
defines their fields.
"""

from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError

from apps.accounts.roles import Capability
from apps.geo.models import LGA, Community
from apps.governance.validators import validate_point_in_bounds

from .base import Column, Importer, RowResult, register, suggest


@register
class CommunityLocationImporter(Importer):
    key = "community-locations"
    label = "Community GPS locations"
    description = ("Add or correct the GPS location of survey communities. The template already lists all "
                   "communities; fill in Latitude and Longitude in decimal degrees (e.g. 4.9247, 6.2649).")
    capability = Capability.MANAGE_REFERENCE
    columns = [
        Column("lga", "LGA", required=True, kind="choice", width=20,
               choices=lambda: list(LGA.objects.active().order_by("name").values_list("name", flat=True)),
               help="Local Government Area. Choose from the list.", example="Southern Ijaw"),
        Column("community", "Community", required=True, max_length=150, width=24,
               help="Community name exactly as listed in the platform.", example="Amassoma"),
        Column("latitude", "Latitude", required=True, kind="decimal", width=14,
               help="Decimal degrees north. Bayelsa latitudes are roughly 4.2 to 5.4.", example="4.9700"),
        Column("longitude", "Longitude", required=True, kind="decimal", width=14,
               help="Decimal degrees east. Bayelsa longitudes are roughly 5.3 to 6.8.", example="6.1000"),
        Column("location_source", "Source of location", max_length=300, width=36,
               help="Who captured the point and how, e.g. 'Field team GPS, March 2026'. "
                    "If blank, the upload's data source name is used.",
               example="Field team handheld GPS, March 2026"),
    ]

    def prepare(self):
        self.lgas = {l.name.lower(): l for l in LGA.objects.active()}
        self.communities = {}
        for c in Community.objects.active().select_related("lga"):
            self.communities.setdefault(c.lga_id, {})[c.name.lower()] = c

    def check_row(self, r: RowResult):
        r.action = "update"
        lga = self.lgas.get((r.values.get("lga") or "").lower())
        name = r.values.get("community")
        if lga and name:
            community = self.communities.get(lga.id, {}).get(name.lower())
            if community is None:
                options = [c.name for c in self.communities.get(lga.id, {}).values()]
                r.error("community", f"'{name}' is not a community in {lga.name}.{suggest(name, options)}")
            else:
                r.target = community
                r.duplicate_key = (community.id,)
                r.values["community_id"] = community.id
        lat, lon = r.values.get("latitude"), r.values.get("longitude")
        if lat is not None and lon is not None:
            try:
                validate_point_in_bounds(Point(lon, lat, srid=4326))
            except ValidationError as e:
                r.error("latitude", e.messages[0])
            else:
                if r.target is not None and r.target.location is not None:
                    old = r.target.location
                    if (round(old.y, 6), round(old.x, 6)) != (round(lat, 6), round(lon, 6)):
                        r.warn("latitude", f"Replaces the current location ({old.y:.5f}, {old.x:.5f}).")

    def save_row(self, values, *, user, batch):
        community = Community.objects.get(pk=values["community_id"])
        community.location = Point(values["longitude"], values["latitude"], srid=4326)
        community.location_source = (values.get("location_source")
                                     or (batch.data_source.name if batch.data_source else "")
                                     or f"Bulk upload: {batch.original_filename}")[:300]
        community._change_reason = f"Bulk upload {batch.pk}"
        community.save()
        return community

    def prefill_rows(self):
        rows = []
        for c in Community.objects.active().filter(is_survey_community=True).select_related("lga") \
                .order_by("lga__name", "name"):
            rows.append({
                "lga": c.lga.name, "community": c.name,
                "latitude": round(c.location.y, 6) if c.location else None,
                "longitude": round(c.location.x, 6) if c.location else None,
                "location_source": c.location_source or None,
            })
        return rows
