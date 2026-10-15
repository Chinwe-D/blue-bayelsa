import pytest
from django.contrib.gis.geos import Point

from apps.geo.models import Community

pytestmark = pytest.mark.django_db


def test_public_lgas_open_to_anonymous(client):
    r = client.get("/api/v1/public/lgas/")
    assert r.status_code == 200
    assert len(r.json()) == 8
    assert all(item["community_count"] == 3 for item in r.json())
    names = [item["name"] for item in r.json()]
    assert names == sorted(names)


def test_public_communities_filter_by_lga(client):
    r = client.get("/api/v1/public/communities/", {"lga__slug": "southern-ijaw"})
    names = {c["name"] for c in r.json()["results"]}
    assert names == {"Amassoma", "Koluama", "Ekensi"}


def test_inactive_community_hidden_from_public(client):
    Community.objects.filter(name="Zarama").update(is_active=False)
    r = client.get("/api/v1/public/communities/", {"search": "Zarama"})
    assert r.json()["count"] == 0
    assert client.get("/api/v1/public/communities/zarama-yenagoa/").status_code == 404


def test_public_serializer_does_not_leak_admin_fields(client):
    r = client.get("/api/v1/public/communities/")
    item = r.json()["results"][0]
    for private in ("is_active", "location_source", "created_at", "updated_at"):
        assert private not in item


def test_geojson_only_includes_located_communities(client):
    Community.objects.filter(name="Amassoma").update(location=Point(6.09, 4.97, srid=4326))
    r = client.get("/api/v1/public/communities/geojson/")
    feats = r.json()["features"]
    assert [f["properties"]["name"] for f in feats] == ["Amassoma"]
    assert feats[0]["geometry"]["coordinates"] == [6.09, 4.97]


def test_public_api_is_read_only(client):
    assert client.post("/api/v1/public/lgas/", {"name": "X"}).status_code in (401, 403, 405)
