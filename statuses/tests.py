from django.test import TestCase
from django.core.exceptions import ValidationError

from .models import StatusDefinition, StatusEntry


class StatusEntryTests(TestCase):
    def test_status_value_must_be_between_0_and_100(self) -> None:
        definition = StatusDefinition.objects.create(name="Rested")
        entry = StatusEntry(status_definition=definition, value=101)

        with self.assertRaises(ValidationError):
            entry.full_clean()
