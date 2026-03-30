"""Seed the database with initial data for TAM Capital."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.database import async_session_factory, init_db
from app.core.security import hash_password
from app.models.tenant import Tenant
from app.models.user import User, UserRole


async def seed():
    """Create initial tenant and admin user."""
    await init_db()

    async with async_session_factory() as session:
        # Create TAM Capital tenant
        tenant = Tenant(
            name="TAM Capital",
            slug="tamcapital",
            primary_color="#222F62",
            accent_color="#1A6DB6",
            default_locale="en",
            disclaimer_text=None,
            config_json={
                "modules_enabled": [
                    "fundamental", "dividend", "earnings", "risk",
                    "technical", "sector", "news", "war",
                    "esg", "peer", "insider"
                ],
                "quick_tickers": ["2222.SR", "1120.SR", "2020.SR", "7010.SR"],
            },
        )
        session.add(tenant)
        await session.flush()

        # Create admin user
        admin = User(
            tenant_id=tenant.id,
            email="admin@tamcapital.com.sa",
            password_hash=hash_password("admin123"),
            full_name="TAM Admin",
            role=UserRole.ADMIN,
            locale="en",
        )
        session.add(admin)

        # Create analyst users
        for name, email in [
            ("Analyst 1", "analyst1@tamcapital.com.sa"),
            ("Analyst 2", "analyst2@tamcapital.com.sa"),
        ]:
            user = User(
                tenant_id=tenant.id,
                email=email,
                password_hash=hash_password("analyst123"),
                full_name=name,
                role=UserRole.ANALYST,
                locale="en",
            )
            session.add(user)

        await session.commit()
        print("Database seeded successfully!")
        print(f"  Tenant: {tenant.name} (ID: {tenant.id})")
        print(f"  Admin: admin@tamcapital.com.sa / admin123")
        print(f"  Analysts: analyst1@tamcapital.com.sa, analyst2@tamcapital.com.sa / analyst123")


if __name__ == "__main__":
    asyncio.run(seed())
