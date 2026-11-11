from wagtail import hooks
from wagtail.permissions import register_permission_policy

from .models import Letter, LetterPermissionPolicy
from .views import ISSUE_LETTER, LetterViewSet

register_permission_policy(Letter, LetterPermissionPolicy(Letter))


@hooks.register("register_admin_viewset")
def register_letters_viewset():
    return LetterViewSet("wagtail_crm_letters")


@hooks.register("register_log_actions")
def register_letter_actions(actions):
    actions.register_action(ISSUE_LETTER, "Issue letter", "Issued letter")
