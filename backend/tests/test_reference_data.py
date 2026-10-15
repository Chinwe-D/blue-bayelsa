import pytest

from apps.geo.models import LGA, Activity, Community

pytestmark = pytest.mark.django_db


def test_seed_matches_project_document():
    assert LGA.objects.count() == 8
    assert Community.objects.count() == 24
    assert Activity.objects.count() == 15
    for lga in LGA.objects.all():
        assert lga.communities.count() == 3, lga.name
    assert set(Community.objects.filter(lga__name="Brass").values_list("name", flat=True)) == {
        "Twon-Brass", "Okpoama", "Fish Town"}


def test_no_invented_coordinates_or_sectors():
    assert not Community.objects.exclude(location__isnull=True).exists()
    assert not Activity.objects.exclude(sector__isnull=True).exists()
