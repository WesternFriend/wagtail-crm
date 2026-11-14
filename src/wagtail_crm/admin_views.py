"""Wagtail's object views for CRM viewsets, refusing before the record lookup.

Wagtail's generic delete, history, usage and inspect views load their record
in setup(), before dispatch() checks permission. A user without permission
then gets "not found" for a missing ID and a refusal for a real one, which
tells them which records exist (#31). These views check first.
"""

from django.core.exceptions import PermissionDenied
from django.views import View
from wagtail.admin.views.generic import history, usage
from wagtail.admin.views.generic import models as generic
from wagtail.admin.views.generic.permissions import PermissionCheckedMixin
from wagtail.admin.viewsets.model import ModelViewSet


class RefuseBeforeLookupMixin(PermissionCheckedMixin, View):
    """Run the view's own permission check in setup(), before get_object()."""

    def setup(self, request, *args, **kwargs):
        self.request = request
        required, any_required = self.permission_required, self.any_permission_required
        if (required is not None and not self.user_has_permission(required)) or (
            any_required is not None and not self.user_has_any_permission(any_required)
        ):
            raise PermissionDenied
        super().setup(request, *args, **kwargs)


class DeleteView(RefuseBeforeLookupMixin, generic.DeleteView):
    pass


class HistoryView(RefuseBeforeLookupMixin, history.HistoryView):
    pass


class UsageView(RefuseBeforeLookupMixin, usage.UsageView):
    pass


class InspectView(RefuseBeforeLookupMixin, generic.InspectView):
    pass


class CRMViewSet(ModelViewSet):
    """A ModelViewSet whose object views refuse before looking the record up."""

    delete_view_class = DeleteView
    history_view_class = HistoryView
    usage_view_class = UsageView
    inspect_view_class = InspectView
