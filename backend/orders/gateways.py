import secrets
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse


@dataclass
class RequestResult:
    authority: str
    redirect_url: str


@dataclass
class VerifyResult:
    success: bool
    ref_id: str = ""


class BaseGateway:
    """قرارداد مشترک همه‌ی درگاه‌ها."""

    name = "base"

    def request(self, *, amount, callback_url, description):
        raise NotImplementedError

    def verify(self, *, authority, amount):
        raise NotImplementedError


class FakeGateway(BaseGateway):
    """درگاه آزمایشی: فقط برای توسعه و تست."""

    name = "fake"

    def request(self, *, amount, callback_url, description):
        if not settings.DEBUG:
            raise ImproperlyConfigured(
                "درگاه آزمایشی فقط در حالت DEBUG مجاز است."
            )
        authority = secrets.token_hex(8).upper()
        return RequestResult(
            authority=authority,
            redirect_url=reverse("orders:fake_bank", args=[authority]),
        )

    def verify(self, *, authority, amount):
        # «بانک» مبلغی را که واقعاً دریافت کرده در cache ثبت کرده است
        paid_amount = cache.get(f"fakebank:{authority}")
        if paid_amount == amount:
            return VerifyResult(success=True, ref_id=f"FAKE-{authority[:6]}")
        return VerifyResult(success=False)


GATEWAYS = {
    FakeGateway.name: FakeGateway,
}


def get_gateway(name=None):
    name = name or settings.PAYMENT_GATEWAY
    try:
        return GATEWAYS[name]()
    except KeyError:
        raise ImproperlyConfigured(f"درگاه ناشناخته: {name}")