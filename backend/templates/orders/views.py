import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from shop.models import Product

from .cart import Cart
from .models import Order, OrderItem


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
    # درگاه آزمایشی: فقط در حالت توسعه
    if not settings.DEBUG:
        raise Http404

    order = get_object_or_404(
        Order, id=order_id, user=request.user, status=Order.Status.PENDING
    )

    if request.method == "POST":
        order.status = Order.Status.PAID
        order.paid_at = timezone.now()
        order.save(update_fields=["status", "paid_at"])
        Cart(request).clear()
        messages.success(request, "پرداخت (آزمایشی) انجام شد.")
        return redirect("orders:purchases")

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