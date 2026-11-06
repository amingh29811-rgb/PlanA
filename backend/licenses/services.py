from datetime import timedelta

from django.utils import timezone

from .models import License


def issue_licenses(order):
    """برای هر آیتم سفارش یک لایسنس می‌سازد (تکرارپذیر و بی‌خطر)."""
    expires_at = timezone.now() + timedelta(days=365)
    for item in order.items.select_related("product"):
        License.objects.get_or_create(
            order_item=item,
            defaults={"product": item.product, "expires_at": expires_at},
        )