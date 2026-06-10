from django.test import TestCase

from .models import Skill, XpEvent, calculate_level


class SkillLevelTests(TestCase):
    def test_calculate_level_uses_balanced_formula(self) -> None:
        cases = (
            (0, 1),
            (99, 1),
            (100, 2),
            (400, 3),
            (900, 4),
            (2500, 6),
            (10000, 11),
        )
        for xp, expected_level in cases:
            with self.subTest(xp=xp):
                self.assertEqual(calculate_level(xp), expected_level)

    def test_skill_total_xp_is_summed_from_xp_events(self) -> None:
        skill = Skill.objects.create(name="Programming")

        XpEvent.objects.create(skill=skill, amount=100, source_type="manual")
        XpEvent.objects.create(skill=skill, amount=75, source_type="manual")

        self.assertEqual(skill.get_total_xp(), 175)
        self.assertEqual(skill.get_level(), 2)

    def test_skill_add_xp_rejects_non_positive_amount(self) -> None:
        skill = Skill.objects.create(name="Programming")

        with self.assertRaises(ValueError):
            skill.add_xp(amount=0, source_type="manual")
