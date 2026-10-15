"""A minimal concrete governed model used only to test the shared workflow."""

from django.db import models

from apps.governance.models import GovernedModel


class SampleRecord(GovernedModel):
    title = models.CharField(max_length=100)

    def __str__(self):
        return self.title
