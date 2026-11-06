from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Activation, License
from schemas import LicenseRequest, LicenseResponse, MessageResponse

app = FastAPI(title="Plan A License API", version="1.0.0")


def utcnow() -> datetime:
    # Django در دیتابیس زمان را به‌صورت UTC (بدون tzinfo) نگه می‌دارد
    return datetime.now(timezone.utc).replace(tzinfo=None)


def fail(status_code: int, code: str, message: str):
    raise HTTPException(
        status_code=status_code, detail={"code": code, "message": message}
    )


def get_active_license(db: Session, key: str) -> License:
    license_ = db.scalar(select(License).where(License.key == key))
    if license_ is None:
        fail(404, "license_not_found", "لایسنس پیدا نشد.")
    if license_.status != "active":
        fail(403, "license_revoked", "این لایسنس غیرفعال شده است.")
    return license_


def find_activation(license_: License, domain: str) -> Activation | None:
    return next((a for a in license_.activations if a.domain == domain), None)


def build_response(license_: License, message: str) -> LicenseResponse:
    expires = license_.expires_at
    return LicenseResponse(
        valid=True,
        message=message,
        updates_until=expires.replace(tzinfo=timezone.utc) if expires else None,
        updates_active=expires is None or expires >= utcnow(),
        activations_used=len(license_.activations),
        activations_max=license_.max_activations,
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/v1/licenses/activate", response_model=LicenseResponse)
def activate(payload: LicenseRequest, db: Session = Depends(get_db)):
    license_ = get_active_license(db, payload.license_key)

    if find_activation(license_, payload.domain) is None:
        if len(license_.activations) >= license_.max_activations:
            fail(
                409,
                "activation_limit_reached",
                "تعداد دامنه‌های مجاز این لایسنس پر شده است.",
            )
        db.add(
            Activation(
                license_id=license_.id,
                domain=payload.domain,
                activated_at=utcnow(),
            )
        )
        db.commit()

    return build_response(license_, "لایسنس برای این دامنه فعال است.")


@app.post("/v1/licenses/validate", response_model=LicenseResponse)
def validate(payload: LicenseRequest, db: Session = Depends(get_db)):
    license_ = get_active_license(db, payload.license_key)

    activation = find_activation(license_, payload.domain)
    if activation is None:
        fail(403, "domain_not_activated", "این لایسنس برای این دامنه فعال نشده است.")

    activation.last_check_at = utcnow()
    db.commit()
    return build_response(license_, "لایسنس معتبر است.")


@app.post("/v1/licenses/deactivate", response_model=MessageResponse)
def deactivate(payload: LicenseRequest, db: Session = Depends(get_db)):
    license_ = get_active_license(db, payload.license_key)

    activation = find_activation(license_, payload.domain)
    if activation is None:
        fail(404, "activation_not_found", "فعال‌سازی‌ای برای این دامنه پیدا نشد.")

    db.delete(activation)
    db.commit()
    return MessageResponse(message="لایسنس از این دامنه برداشته شد.")