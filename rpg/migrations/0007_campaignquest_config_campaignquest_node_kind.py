from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rpg", "0006_alter_achievement_trigger_type_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="campaignquest",
            name="config",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="campaignquest",
            name="node_kind",
            field=models.CharField(
                choices=[
                    ("quest", "Quest"),
                    ("milestone", "Milestone"),
                    ("reward", "Reward"),
                    ("reflection", "Reflection"),
                    ("gate", "Gate"),
                ],
                default="quest",
                max_length=20,
            ),
        ),
    ]
