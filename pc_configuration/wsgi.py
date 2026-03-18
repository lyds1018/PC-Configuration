import os
import sys
from pathlib import Path

from django.core.wsgi import get_wsgi_application

BASE_DIR = Path(__file__).resolve().parent.parent
APPS_DIR = BASE_DIR / "pc_configuration" / "apps"
sys.path.insert(0, str(APPS_DIR))


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pc_configuration.settings")

application = get_wsgi_application()
