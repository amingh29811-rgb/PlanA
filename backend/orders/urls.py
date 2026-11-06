from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("cart/", views.cart_detail, name="cart"),
    path("cart/add/<int:product_id>/", views.cart_add, name="cart_add"),
    path("cart/remove/<int:product_id>/", views.cart_remove, name="cart_remove"),
    path("checkout/", views.checkout, name="checkout"),
    path("pay/<int:order_id>/", views.pay, name="pay"),
    path("purchases/", views.purchases, name="purchases"),
    path("download/<int:product_id>/", views.download, name="download"),
]