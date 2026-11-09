from django.apps import AppConfig


class ContactsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "wagtail_crm.contacts"
    label = "wagtail_crm_contacts"
    verbose_name = "Contacts"
