import os
import logging
from django.core.wsgi import get_wsgi_application
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaminghub.settings')

application = get_wsgi_application()
app = application

if os.getenv('VERCEL'):
    try:
        call_command('migrate', interactive=False)
    except Exception as e:
        logging.error(f"Cold boot database migration notice: {e}")
