from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import License


@login_required
def my_licenses(request):
    licenses = (
        License.objects.filter(order_item__order__user=request.user)
        .select_related("product")
        .prefetch_related("activations")
    )
    return render(request, "licenses/my_licenses.html", {"licenses": licenses})