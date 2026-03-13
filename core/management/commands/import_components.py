from django.core.management.base import BaseCommand

from core.importers import import_csvs


class Command(BaseCommand):
    help = 'Import all CSV components from data/csv into the database'

    def handle(self, *args, **options):
        results = import_csvs()
        for category, count in results.items():
            self.stdout.write(self.style.SUCCESS(f'{category}: {count} items'))