from django.db import models
from django.conf import settings
from django.core.files.storage import FileSystemStorage


def private_storage():
    return FileSystemStorage(location=settings.PRIVATE_FILES_ROOT)

# Create your models here.

class Category(models.Model):
    name = models.CharField("نام", max_length=100, unique=True)
    slug = models.SlugField("اسلاگ(انگلیسی)", unique=True)

    class Meta:
        verbose_name = "دسته"
        verbose_name_plural = "دسته ها"

    def __str__(self):
        return self.name


class Product(models.Model):
    class ProductType(models.TextChoices):
        THEME = "theme", "قالب"
        PLUGIN = "plugin", "افزونه"

    name = models.CharField("نام", max_length=200)
    slug = models.SlugField("اسلاگ(انگلیسی)", unique=True)
    product_type = models.CharField(
        "نوع", max_length=10, choices=ProductType.choices
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="دسته",

    )
    price = models.PositiveBigIntegerField("قیمت(تومان)")
    description = models.TextField("توضیحات", blank=True)
    image = models.ImageField('تصویر', upload_to="products/", blank=True)
    file = models.FileField(
        "فایل  محصول ",
        upload_to = "products/",
        storage= private_storage,
        blank=True,
    )
    is_active = models.BooleanField("موجود", default=True)
    created_at = models.DateTimeField('تاریخ ایجاد', auto_now_add=True)

    class Meta:
        verbose_name = "محصول"
        verbose_name_plural = "محصولات"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name
