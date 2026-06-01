from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("build_history", "0001_initial"),
        ("pc_builder", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[migrations.DeleteModel(name="BuildHistory")],
        )
    ]
