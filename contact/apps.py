# contact/apps.py
from django.apps import AppConfig

class ContactConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'contact'
    
    def ready(self):
        # Import signals if you plan to add any
        try:
            import contact.signals
        except ImportError:
            pass