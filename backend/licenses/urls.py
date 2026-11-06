from django.urls import path

from . import views

app_name = "licenses"

urlpatterns = [
    path("licenses/", views.my_licenses, name="mine"),
]