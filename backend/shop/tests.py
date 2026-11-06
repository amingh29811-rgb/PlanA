from django.test import TestCase
from django.urls import reverse

from .models import Category, Product


class ShopPageTests(TestCase):
    def setUp(self):
        category = Category.objects.create(name="فروشگاهی", slug="shop")
        self.active = Product.objects.create(
            name="Alpha Theme",
            slug="alpha-theme",
            product_type="theme",
            category=category,
            price=100000,
        )
        self.hidden = Product.objects.create(
            name="Hidden Theme",
            slug="hidden-theme",
            product_type="theme",
            category=category,
            price=100000,
            is_active=False,
        )

    def test_home_shows_only_active_products(self):
        response = self.client.get(reverse("shop:home"))
        self.assertContains(response, "Alpha Theme")
        self.assertNotContains(response, "Hidden Theme")

    def test_active_product_detail_loads(self):
        response = self.client.get(reverse("shop:product_detail", args=["alpha-theme"]))
        self.assertEqual(response.status_code, 200)

    def test_inactive_product_detail_is_404(self):
        response = self.client.get(reverse("shop:product_detail", args=["hidden-theme"]))
        self.assertEqual(response.status_code, 404)

    def test_unknown_product_is_404(self):
        response = self.client.get(reverse("shop:product_detail", args=["no-such-slug"]))
        self.assertEqual(response.status_code, 404)