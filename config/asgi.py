"""
ASGI config for PC Configuration project.
"""

import os
import sys
from pathlib import Path

from django.core.asgi import get_asgi_application

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent.parent
APPS_DIR = BASE_DIR / "apps"
if str(APPS_DIR) not in sys.path:
    sys.path.insert(0, str(APPS_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_asgi_application()
