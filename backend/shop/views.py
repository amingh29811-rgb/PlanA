from django.shortcuts import render, get_object_or_404
from .models import Product
# Create your views here.


def home(request):
    products = Product.objects.filter(is_active=True)[:6]
    return render(request, "shop/home.html", {"product": products})


def product_detail(request, slug):
    product = get_object_or_404(product, slug=slug, is_active=True)
    return render(request, "shop/product_detail.html", {"product": product})