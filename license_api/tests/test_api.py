from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from database import get_db
from main import app, utcnow
from models import Activation, Base, License

KEY = "PLANA-AAAAAA-BBBBBB-CCCCCC-DDDDDD"


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture()
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_license(db, key=KEY, max_activations=1, status="active", expires_in_days=365):
    license_ = License(
        key=key,
        status=status,
        max_activations=max_activations,
        expires_at=utcnow() + timedelta(days=expires_in_days),
    )
    db.add(license_)
    db.commit()
    return license_


def call(client, action, domain="example.com", key=KEY):
    return client.post(
        f"/v1/licenses/{action}", json={"license_key": key, "domain": domain}
    )


def error_code(response):
    return response.json()["detail"]["code"]


def test_activate_success(client, db):
    make_license(db)
    response = call(client, "activate")
    body = response.json()
    assert response.status_code == 200
    assert body["valid"] is True
    assert body["activations_used"] == 1
    assert body["activations_max"] == 1


def test_activate_same_domain_twice_is_idempotent(client, db):
    make_license(db)
    assert call(client, "activate").status_code == 200
    assert call(client, "activate").status_code == 200
    assert len(db.scalars(select(Activation)).all()) == 1


def test_domain_is_normalized(client, db):
    make_license(db)
    call(client, "activate", domain="https://WWW.Example.com/shop/")
    assert db.scalar(select(Activation.domain)) == "example.com"
    assert call(client, "validate", domain="www.example.com").status_code == 200


def test_activation_limit_returns_409(client, db):
    make_license(db, max_activations=1)
    assert call(client, "activate", domain="a.com").status_code == 200
    response = call(client, "activate", domain="b.com")
    assert response.status_code == 409
    assert error_code(response) == "activation_limit_reached"


def test_unknown_key_returns_404(client):
    response = call(client, "activate")
    assert response.status_code == 404
    assert error_code(response) == "license_not_found"


def test_revoked_license_returns_403(client, db):
    make_license(db, status="revoked")
    response = call(client, "activate")
    assert response.status_code == 403
    assert error_code(response) == "license_revoked"


def test_validate_requires_activation(client, db):
    make_license(db)
    response = call(client, "validate")
    assert response.status_code == 403
    assert error_code(response) == "domain_not_activated"


def test_validate_records_last_check(client, db):
    make_license(db)
    call(client, "activate")
    assert call(client, "validate").status_code == 200
    db.expire_all()
    assert db.scalar(select(Activation.last_check_at)) is not None


def test_deactivate_frees_the_slot(client, db):
    make_license(db, max_activations=1)
    call(client, "activate", domain="a.com")
    assert call(client, "deactivate", domain="a.com").status_code == 200
    assert call(client, "activate", domain="b.com").status_code == 200


def test_deactivate_unknown_domain_returns_404(client, db):
    make_license(db)
    response = call(client, "deactivate", domain="nope.com")
    assert response.status_code == 404
    assert error_code(response) == "activation_not_found"


def test_expired_license_still_works_but_has_no_updates(client, db):
    make_license(db, expires_in_days=-1)
    response = call(client, "activate")
    assert response.status_code == 200
    assert response.json()["updates_active"] is False


def test_invalid_domain_returns_422(client, db):
    make_license(db)
    assert call(client, "activate", domain="///").status_code == 422