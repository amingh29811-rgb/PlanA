from shop.models import Product


class Cart:
    SESSION_KEY = "cart"

    def __init__(self, request):
        self.session = request.session
        self.ids = self.session.get(self.SESSION_KEY, [])

    def _save(self):
        self.session[self.SESSION_KEY] = self.ids
        self.session.modified = True

    def add(self, product_id):
        if product_id not in self.ids:
            self.ids.append(product_id)
            self._save()

    def remove(self, product_id):
        if product_id in self.ids:
            self.ids.remove(product_id)
            self._save()

    def clear(self):
        self.ids = []
        self._save()

    def products(self):
        return Product.objects.filter(id__in=self.ids, is_active=True)

    def total(self):
        return sum(p.price for p in self.products())

    def __len__(self):
        return len(self.ids)