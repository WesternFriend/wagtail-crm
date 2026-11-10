from wagtail import hooks

from .views import ACCEPT_RECONCILIATION, PaymentViewSet, ReconciliationViewSet


@hooks.register("register_admin_viewset")
def register_payments_viewset():
    return PaymentViewSet("wagtail_crm_payments")


@hooks.register("register_admin_viewset")
def register_reconciliations_viewset():
    return ReconciliationViewSet("wagtail_crm_reconciliations")


@hooks.register("register_log_actions")
def register_reconciliation_actions(actions):
    actions.register_action(
        ACCEPT_RECONCILIATION, "Accept reconciliation", "Accepted reconciliation"
    )
