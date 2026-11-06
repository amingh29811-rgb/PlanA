from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class License(Base):
    __tablename__ = "licenses_license"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(10))
    max_activations: Mapped[int]
    expires_at: Mapped[datetime | None]

    activations: Mapped[list["Activation"]] = relationship(back_populates="license")


class Activation(Base):
    __tablename__ = "licenses_activation"

    id: Mapped[int] = mapped_column(primary_key=True)
    license_id: Mapped[int] = mapped_column(ForeignKey("licenses_license.id"))
    domain: Mapped[str] = mapped_column(String(255))
    activated_at: Mapped[datetime]
    last_check_at: Mapped[datetime | None]

    license: Mapped["License"] = relationship(back_populates="activations")