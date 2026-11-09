from wagtail import hooks

from .views import PaymentViewSet


@hooks.register("register_admin_viewset")
def register_payments_viewset():
    return PaymentViewSet("wagtail_crm_payments")
