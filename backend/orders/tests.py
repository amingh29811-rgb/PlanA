from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ImproperlyConfigured
from shop.models import Category, Product
from .models import Order, OrderItem, Payment
from django.core.cache import cache
from .models import Order, OrderItem
from licenses.models import License

User = get_user_model()


# ---------- توابع کمکی (برای جلوگیری از تکرار) ----------

def make_user(username):
    return User.objects.create_user(
        username, f"{username}@example.com", "pass12345!"
    )


def make_product(slug="test-theme", price=100000, **extra):
    category, _ = Category.objects.get_or_create(name="فروشگاهی", slug="shop")
    return Product.objects.create(
        name=f"محصول {slug}",
        slug=slug,
        product_type="theme",
        category=category,
        price=price,
        **extra,
    )


def make_paid_order(user, product):
    order = Order.objects.create(
        user=user,
        status=Order.Status.PAID,
        total=product.price,
        paid_at=timezone.now(),
    )
    OrderItem.objects.create(
        order=order, product=product, price_at_purchase=product.price
    )
    return order


# ---------- دانلود امن ----------

class DownloadSecurityTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner")
        self.other = make_user("other")
        self.product = make_product()
        self.product.file.save("test.zip", ContentFile(b"zipdata"), save=True)
        self.addCleanup(self.product.file.delete, save=False)
        make_paid_order(self.owner, self.product)
        self.url = reverse("orders:download", args=[self.product.id])

    def test_anonymous_user_is_sent_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_owner_can_download(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"zipdata")
        response.close()

    def test_other_user_gets_403(self):
        self.client.force_login(self.other)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_pending_order_does_not_grant_access(self):
        buyer = make_user("buyer")
        order = Order.objects.create(user=buyer, total=self.product.price)
        OrderItem.objects.create(
            order=order, product=self.product, price_at_purchase=self.product.price
        )
        self.client.force_login(buyer)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)


# ---------- سبد خرید ----------

class CartTests(TestCase):
    def setUp(self):
        self.product = make_product()
        self.add_url = reverse("orders:cart_add", args=[self.product.id])

    def test_add_returns_item_count(self):
        response = self.client.post(self.add_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 1)

    def test_same_product_is_not_added_twice(self):
        self.client.post(self.add_url)
        response = self.client.post(self.add_url)
        self.assertEqual(response.json()["count"], 1)

    def test_add_requires_post(self):
        response = self.client.get(self.add_url)
        self.assertEqual(response.status_code, 405)

    def test_inactive_product_cannot_be_added(self):
        self.product.is_active = False
        self.product.save()
        response = self.client.post(self.add_url)
        self.assertEqual(response.status_code, 404)

    def test_already_purchased_product_returns_409(self):
        user = make_user("buyer")
        make_paid_order(user, self.product)
        self.client.force_login(user)
        response = self.client.post(self.add_url)
        self.assertEqual(response.status_code, 409)


# ---------- ثبت سفارش ----------

class CheckoutTests(TestCase):
    def setUp(self):
        self.user = make_user("buyer")
        self.product = make_product(price=490000)
        self.client.force_login(self.user)
        self.client.post(reverse("orders:cart_add", args=[self.product.id]))

    def test_checkout_creates_pending_order_with_database_price(self):
        response = self.client.post(reverse("orders:checkout"))
        order = Order.objects.get(user=self.user)
        self.assertRedirects(
            response,
            reverse("orders:pay", args=[order.id]),
            fetch_redirect_response=False,
        )
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(order.total, 490000)

    def test_price_snapshot_survives_later_price_change(self):
        self.client.post(reverse("orders:checkout"))
        self.product.price = 999999
        self.product.save()
        item = OrderItem.objects.get()
        self.assertEqual(item.price_at_purchase, 490000)

    def test_empty_cart_creates_no_order(self):
        self.client.post(reverse("orders:cart_remove", args=[self.product.id]))
        self.client.post(reverse("orders:checkout"))
        self.assertEqual(Order.objects.count(), 0)

    def test_checkout_requires_login(self):
        self.client.logout()
        response = self.client.post(reverse("orders:checkout"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Order.objects.count(), 0)


# ---------- دسترسی به صفحه‌ی پرداخت ----------

class PayAccessTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner")
        self.intruder = make_user("intruder")
        self.order = Order.objects.create(user=self.owner, total=1000)
        self.url = reverse("orders:pay", args=[self.order.id])

    @override_settings(DEBUG=True)
    def test_user_cannot_open_another_users_order(self):
        self.client.force_login(self.intruder)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

    @override_settings(DEBUG=True)
    def test_owner_can_open_own_order_in_debug(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_fake_gateway_is_disabled_when_debug_is_off(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)

        def test_fake_gateway_refuses_to_start_when_debug_is_off(self):
          self.client.force_login(self.owner)
          with self.assertRaises(ImproperlyConfigured):
               self.client.post(self.url)

    @override_settings(DEBUG=True)


class PaymentFlowTests(TestCase):
    def setUp(self):
        self.user = make_user("buyer")
        self.product = make_product(price=490000)
        self.order = Order.objects.create(user=self.user, total=490000)
        OrderItem.objects.create(
            order=self.order, product=self.product, price_at_purchase=490000
        )
        self.client.force_login(self.user)
    def test_successful_payment_issues_license(self):
        payment = self.start_payment()
        self.pay_at_bank(payment)
        self.callback(payment)
        self.assertEqual(
            License.objects.filter(order_item__order=self.order).count(), 1
        )

    def test_failed_payment_issues_no_license(self):
        payment = self.start_payment()
        self.callback(payment, status="OK")  # جعلی، بدون پرداخت در بانک
        self.assertEqual(License.objects.count(), 0)

    # ----- توابع کمکی برای شبیه‌سازی هر مرحله -----

    def start_payment(self):
        response = self.client.post(reverse("orders:pay", args=[self.order.id]))
        payment = Payment.objects.get(order=self.order)
        self.assertRedirects(
            response,
            reverse("orders:fake_bank", args=[payment.authority]),
            fetch_redirect_response=False,
        )
        return payment

    def pay_at_bank(self, payment, action="pay"):
        return self.client.post(
            reverse("orders:fake_bank", args=[payment.authority]),
            {"action": action},
        )

    def callback(self, payment, status="OK"):
        return self.client.get(
            reverse("orders:callback"),
            {"Authority": payment.authority, "Status": status},
        )

    # ----- تست‌ها -----

    def test_successful_payment_marks_order_paid(self):
        payment = self.start_payment()
        self.pay_at_bank(payment)
        self.callback(payment)

        self.order.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PAID)
        self.assertEqual(payment.status, Payment.Status.SUCCESS)
        self.assertTrue(payment.ref_id)
        self.assertIsNotNone(self.order.paid_at)

    def test_cancelled_payment_leaves_order_pending(self):
        payment = self.start_payment()
        self.pay_at_bank(payment, action="cancel")
        self.callback(payment, status="NOK")

        self.order.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PENDING)
        self.assertEqual(payment.status, Payment.Status.FAILED)

    def test_forged_callback_without_paying_is_rejected(self):
        payment = self.start_payment()
        # کاربر بانک را دور زده و مستقیم آدرس بازگشت را باز کرده
        self.callback(payment, status="OK")

        self.order.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PENDING)
        self.assertEqual(payment.status, Payment.Status.FAILED)

    def test_amount_mismatch_is_rejected(self):
        payment = self.start_payment()
        # بانک مبلغ کمتری از مبلغ سفارش دریافت کرده
        cache.set(f"fakebank:{payment.authority}", 1000, 600)
        self.callback(payment, status="OK")

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PENDING)

    def test_repeated_callback_is_harmless(self):
        payment = self.start_payment()
        self.pay_at_bank(payment)
        self.callback(payment)
        self.order.refresh_from_db()
        first_paid_at = self.order.paid_at

        self.callback(payment)
        self.order.refresh_from_db()
        self.assertEqual(self.order.paid_at, first_paid_at)
        self.assertEqual(
            Payment.objects.filter(status=Payment.Status.SUCCESS).count(), 1
        )

    def test_unknown_authority_returns_404(self):
        response = self.client.get(
            reverse("orders:callback"), {"Authority": "NOPE", "Status": "OK"}
        )
        self.assertEqual(response.status_code, 404)

    def test_paid_product_becomes_downloadable(self):
        self.product.file.save("t.zip", ContentFile(b"x"), save=True)
        self.addCleanup(self.product.file.delete, save=False)

        payment = self.start_payment()
        self.pay_at_bank(payment)
        self.callback(payment)

        response = self.client.get(reverse("orders:download", args=[self.product.id]))
        self.assertEqual(response.status_code, 200)
        response.close()