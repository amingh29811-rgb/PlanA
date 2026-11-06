import logging
import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from licenses.services import issue_licenses

from shop.models import Product

from .cart import Cart
from .gateways import get_gateway
from .models import Order, OrderItem, Payment

logger = logging.getLogger(__name__)

def user_owns(user, product_id):
    return user.is_authenticated and OrderItem.objects.filter(
        order__user=user,
        order__status=Order.Status.PAID,
        product_id=product_id,
    ).exists()


@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)

    if user_owns(request.user, product.id):
        return JsonResponse({"error": "این محصول را قبلاً خریده‌اید"}, status=409)

    cart = Cart(request)
    cart.add(product.id)
    return JsonResponse({"count": len(cart)})


def cart_detail(request):
    cart = Cart(request)
    return render(
        request,
        "orders/cart.html",
        {"products": cart.products(), "total": cart.total()},
    )


@require_POST
def cart_remove(request, product_id):
    Cart(request).remove(product_id)
    return redirect("orders:cart")


@login_required
@require_POST
def checkout(request):
    cart = Cart(request)
    products = list(cart.products())

    if not products:
        messages.error(request, "سبد خرید خالی است.")
        return redirect("orders:cart")

    with transaction.atomic():
        order = Order.objects.create(user=request.user)
        total = 0
        for product in products:
            OrderItem.objects.create(
                order=order,
                product=product,
                price_at_purchase=product.price,  # قیمت از دیتابیس
            )
            total += product.price
        order.total = total
        order.save(update_fields=["total"])

    return redirect("orders:pay", order_id=order.id)

@login_required
def pay(request, order_id):
    order = get_object_or_404(
        Order, id=order_id, user=request.user, status=Order.Status.PENDING
    )

    if request.method == "POST":
        gateway = get_gateway()
        callback_url = request.build_absolute_uri(reverse("orders:callback"))

        result = gateway.request(
            amount=order.total,
            callback_url=callback_url,
            description=f"سفارش #{order.id}",
        )
        Payment.objects.create(
            order=order,
            gateway=gateway.name,
            authority=result.authority,
            amount=order.total,
        )
        return redirect(result.redirect_url)

    return render(request, "orders/pay.html", {"order": order})


@login_required
def purchases(request):
    items = (
        OrderItem.objects.filter(
            order__user=request.user, order__status=Order.Status.PAID
        )
        .select_related("product", "order")
        .order_by("-order__paid_at")
    )
    return render(request, "orders/purchases.html", {"items": items})


@login_required
def download(request, product_id):
    if not user_owns(request.user, product_id):
        raise PermissionDenied

    product = get_object_or_404(Product, id=product_id)
    if not product.file:
        raise Http404

    return FileResponse(
        product.file.open("rb"),
        as_attachment=True,
        filename=os.path.basename(product.file.name),
    )


def payment_callback(request):
    authority = request.GET.get("Authority", "")
    gateway_status = request.GET.get("Status", "")

    with transaction.atomic():
        payment = get_object_or_404(
            Payment.objects.select_for_update().select_related("order"),
            authority=authority,
        )

        order.status = Order.Status.PAID
        order.paid_at = now
        order.save(update_fields=["status", "paid_at"])

        issue_licenses(order)   # ← جدید
        order = payment.order

        # بازگشت تکراری (مثلاً کاربر صفحه را رفرش کرده)
        if payment.status == Payment.Status.SUCCESS:
            messages.info(request, "این پرداخت قبلاً تأیید شده است.")
            return redirect("orders:purchases")

        # کاربر در درگاه انصراف داده
        if gateway_status != "OK":
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status"])
            messages.error(request, "پرداخت انجام نشد یا لغو شد.")
            return redirect("orders:pay", order_id=order.id)

        # تأیید سرور به سرور (مرجع حقیقت)
        gateway = get_gateway(payment.gateway)
        result = gateway.verify(authority=payment.authority, amount=payment.amount)

        if not result.success or payment.amount != order.total:
            logger.warning(
                "Payment verification failed: payment=%s order=%s",
                payment.id,
                order.id,
            )
            payment.status = Payment.Status.FAILED
            payment.save(update_fields=["status"])
            messages.error(
                request,
                "تأیید پرداخت ناموفق بود. اگر مبلغی از حساب شما کسر شده، "
                "با پشتیبانی تماس بگیرید.",
            )
            return redirect("orders:pay", order_id=order.id)

        now = timezone.now()
        payment.status = Payment.Status.SUCCESS
        payment.ref_id = result.ref_id
        payment.verified_at = now
        payment.save(update_fields=["status", "ref_id", "verified_at"])

        order.status = Order.Status.PAID
        order.paid_at = now
        order.save(update_fields=["status", "paid_at"])

    # فقط محصولات همین سفارش را از سبد بردار
    cart = Cart(request)
    for product_id in order.items.values_list("product_id", flat=True):
        cart.remove(product_id)

    messages.success(request, "پرداخت با موفقیت انجام شد.")
    return redirect("orders:purchases")


def fake_bank(request, authority):
    if not settings.DEBUG:
        raise Http404

    payment = get_object_or_404(
        Payment,
        authority=authority,
        gateway="fake",
        status=Payment.Status.INITIATED,
    )
    callback = reverse("orders:callback")

    if request.method == "POST":
        if request.POST.get("action") == "pay":
            # بانک مبلغ را دریافت کرد و ثبت می‌کند
            cache.set(f"fakebank:{authority}", payment.amount, 600)
            return redirect(f"{callback}?Authority={authority}&Status=OK")
        return redirect(f"{callback}?Authority={authority}&Status=NOK")

    return render(request, "orders/fake_bank.html", {"payment": payment})