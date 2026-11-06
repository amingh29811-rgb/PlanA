from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from orders.models import Order, OrderItem
from shop.models import Category, Product

from .models import License
from .services import issue_licenses

User = get_user_model()


def make_paid_order(username="buyer", slugs=("alpha",)):
    user = User.objects.create_user(
        username, f"{username}@example.com", "pass12345!"
    )
    category, _ = Category.objects.get_or_create(name="فروشگاهی", slug="shop")
    order = Order.objects.create(
        user=user, status=Order.Status.PAID, total=0, paid_at=timezone.now()
    )
    for slug in slugs:
        product = Product.objects.create(
            name=slug, slug=slug, product_type="plugin",
            category=category, price=1000,
        )
        OrderItem.objects.create(order=order, product=product, price_at_purchase=1000)
    return user, order


class IssueLicenseTests(TestCase):
    def test_one_license_per_item(self):
        _, order = make_paid_order(slugs=("a", "b"))
        issue_licenses(order)
        self.assertEqual(License.objects.count(), 2)

    def test_issue_is_idempotent(self):
        _, order = make_paid_order()
        issue_licenses(order)
        issue_licenses(order)
        self.assertEqual(License.objects.count(), 1)

    def test_key_format(self):
        _, order = make_paid_order()
        issue_licenses(order)
        self.assertRegex(License.objects.get().key, r"^PLANA(-[0-9A-F]{6}){4}$")

    def test_keys_are_unique(self):
        _, order = make_paid_order(slugs=("a", "b"))
        issue_licenses(order)
        keys = list(License.objects.values_list("key", flat=True))
        self.assertEqual(len(keys), len(set(keys)))


class MyLicensesViewTests(TestCase):
    def test_requires_login(self):
        response = self.client.get(reverse("licenses:mine"))
        self.assertEqual(response.status_code, 302)

    def test_user_sees_only_own_licenses(self):
        user_a, order_a = make_paid_order("a", ("alpha",))
        _, order_b = make_paid_order("b", ("beta",))
        issue_licenses(order_a)
        issue_licenses(order_b)

        self.client.force_login(user_a)
        response = self.client.get(reverse("licenses:mine"))

        self.assertContains(response, License.objects.get(order_item__order=order_a).key)
        self.assertNotContains(response, License.objects.get(order_item__order=order_b).key)