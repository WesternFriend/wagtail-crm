from django.apps import AppConfig


class LettersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "wagtail_crm.letters"
    label = "wagtail_crm_letters"
    verbose_name = "Letters"
