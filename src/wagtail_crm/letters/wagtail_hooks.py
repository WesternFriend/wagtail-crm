from wagtail import hooks
from wagtail.permissions import register_permission_policy

from .models import Dispatch, Letter, RefusingPermissionPolicy
from .views import ISSUE_LETTER, DispatchViewSet, LetterViewSet

# Issued letters never change: a correction is a new letter. A dispatch can
# be corrected (History keeps the edit) but not removed.
register_permission_policy(
    Letter, RefusingPermissionPolicy(Letter, refused={"change", "delete"})
)
register_permission_policy(
    Dispatch, RefusingPermissionPolicy(Dispatch, refused={"delete"})
)


@hooks.register("register_admin_viewset")
def register_letters_viewset():
    return LetterViewSet("wagtail_crm_letters")


@hooks.register("register_admin_viewset")
def register_dispatches_viewset():
    return DispatchViewSet("wagtail_crm_dispatches")


@hooks.register("register_log_actions")
def register_letter_actions(actions):
    actions.register_action(ISSUE_LETTER, "Issue letter", "Issued letter")
