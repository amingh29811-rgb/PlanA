from django.conf import settings
from django.db import models

from shop.models import Product


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "در انتظار پرداخت"
        PAID = "paid", "پرداخت‌شده"
        CANCELED = "canceled", "لغو شده"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name="کاربر",
    )
    status = models.CharField(
        "وضعیت", max_length=10, choices=Status.choices, default=Status.PENDING
    )
    total = models.PositiveIntegerField("جمع کل (تومان)", default=0)
    created_at = models.DateTimeField("تاریخ ایجاد", auto_now_add=True)
    paid_at = models.DateTimeField("تاریخ پرداخت", null=True, blank=True)

    class Meta:
        verbose_name = "سفارش"
        verbose_name_plural = "سفارش‌ها"
        ordering = ["-created_at"]

    def __str__(self):
        return f"سفارش #{self.pk}"



class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="order_items"
    )
    price_at_purchase = models.PositiveIntegerField("قیمت در زمان خرید")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["order", "product"], name="unique_product_per_order"
            )
        ]

    def __str__(self):
        return f"{self.product} در {self.order}"

class Payment(models.Model):
    class Status(models.TextChoices):
        INITIATED = "initiated", "شروع شده"
        SUCCESS = "success", "موفق"
        FAILED = "failed", "ناموفق"

    order = models.ForeignKey(
        Order, on_delete=models.PROTECT, related_name="payments"
    )
    gateway = models.CharField("درگاه", max_length=30)
    authority = models.CharField("شناسه تراکنش", max_length=100, unique=True)
    amount = models.PositiveIntegerField("مبلغ (تومان)")
    status = models.CharField(
        "وضعیت", max_length=10, choices=Status.choices, default=Status.INITIATED
    )
    ref_id = models.CharField("کد پیگیری", max_length=100, blank=True)
    created_at = models.DateTimeField("تاریخ ایجاد", auto_now_add=True)
    verified_at = models.DateTimeField("تاریخ تأیید", null=True, blank=True)

    class Meta:
        verbose_name = "پرداخت"
        verbose_name_plural = "پرداخت‌ها"
        ordering = ["-created_at"]

    def __str__(self):
        return f"پرداخت {self.authority} ({self.get_status_display()})"