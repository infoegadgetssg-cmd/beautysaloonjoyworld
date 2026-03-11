from django.apps import AppConfig


class ServicesConfig(AppConfig):
    name = 'services'

    # def ready(self):
    #     import logging
    #     from django.db import connection

    #     logger = logging.getLogger(__name__)
    #     try:
    #         tables = connection.introspection.table_names()
    #         if 'services_service' not in tables:
    #             logger.error("Services table does not exist. Did you forget to run migrations?")
    #     except Exception:
    #         # Do not crash app startup if database is unavailable during initialization.
    #         pass
