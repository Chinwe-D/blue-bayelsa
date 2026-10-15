"""
Seed reference data taken directly from the project document
"BLUE-BAYELSA SURVEY: Communities and Enterprises".

Only names are seeded. GPS coordinates and LGA boundaries are left empty
until they are supplied by the field team or an approved boundary source.
"""

from django.db import migrations
from django.utils.text import slugify

SURVEY_COMMUNITIES = {
    "Nembe": ["Bassambiri", "Ogbolomabiri", "Fantuo"],
    "Brass": ["Twon-Brass", "Okpoama", "Fish Town"],
    "Sagbama": ["Ebedebiri", "Sagbama Town", "Angalabiri"],
    "Yenagoa": ["Swali", "Tombia", "Zarama"],
    "Ekeremor": ["Aleibiri", "Agge", "Bilabiri"],
    "Kolokuma/Opokuma": ["Sampou", "Kaiama", "Sabagreia"],
    "Ogbia": ["Ogbia Town", "Ayakoro", "Anyama-Ogbia"],
    "Southern Ijaw": ["Amassoma", "Koluama", "Ekensi"],
}

ACTIVITIES = [
    "Artisanal fishing in rivers, creeks, estuaries and coastal waters",
    "Fish farming and aquaculture",
    "Fish smoking and drying",
    "Fresh and processed fish marketing",
    "Shrimp and prawn harvesting",
    "Periwinkle, crab and oyster collection",
    "Passenger transportation by boats, canoes and ferries",
    "Waterborne transportation of goods and agricultural produce",
    "Canoe and boat construction",
    "Boat and outboard-engine repairs",
    "Production and sale of fishing nets, traps, hooks and other equipment",
    "Cold storage, ice production and preservation of seafood",
    "Mangrove-resource harvesting and conservation",
    "Sand dredging and related river-based activities",
    "Waterfront recreation, fishing festivals, boat regattas and coastal tourism",
]


def seed(apps, schema_editor):
    LGA = apps.get_model("geo", "LGA")
    Community = apps.get_model("geo", "Community")
    Activity = apps.get_model("geo", "Activity")
    for lga_name, communities in SURVEY_COMMUNITIES.items():
        lga, _ = LGA.objects.get_or_create(name=lga_name, defaults={"slug": slugify(lga_name)})
        for name in communities:
            Community.objects.get_or_create(
                lga=lga, name=name,
                defaults={"slug": slugify(f"{name}-{lga_name}"), "is_survey_community": True},
            )
    for order, name in enumerate(ACTIVITIES, start=1):
        Activity.objects.get_or_create(
            name=name, defaults={"slug": slugify(name)[:200], "display_order": order}
        )


def unseed(apps, schema_editor):
    apps.get_model("geo", "Community").objects.filter(
        name__in=[c for cs in SURVEY_COMMUNITIES.values() for c in cs]).delete()
    apps.get_model("geo", "LGA").objects.filter(name__in=SURVEY_COMMUNITIES).delete()
    apps.get_model("geo", "Activity").objects.filter(name__in=ACTIVITIES).delete()


class Migration(migrations.Migration):
    dependencies = [("geo", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
