import asyncio
import sys
import os

# Add parent directory to sys.path so app modules are resolvable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.models.tenant import Tenant
from app.models.membership import TenantMember, TenantRole
from app.models.project import Project, Task, TaskStatus, TaskPriority
from app.models.audit_log import AuditLog
from app.core.logging import logger, setup_logging


async def seed_data():
    setup_logging()
    logger.info("--> Seeding demo database for NovaPulse SaaS...")

    async with AsyncSessionLocal() as session:
        # Check if already seeded
        res = await session.execute(select(User).where(User.email == "owner@novapulse.io"))
        if res.scalar_one_or_none():
            logger.info("Database already seeded with demo data.")
            return

        # 1. Create Users
        owner_user = User(
            email="owner@novapulse.io",
            hashed_password=hash_password("Password123!"),
            full_name="Alex Mercer (Owner)",
            is_active=True,
            is_superuser=True,
        )
        admin_user = User(
            email="admin@novapulse.io",
            hashed_password=hash_password("Password123!"),
            full_name="Samantha Ray (Admin)",
            is_active=True,
            is_superuser=False,
        )
        member_user = User(
            email="dev@novapulse.io",
            hashed_password=hash_password("Password123!"),
            full_name="Jordan Lee (Engineer)",
            is_active=True,
            is_superuser=False,
        )
        session.add_all([owner_user, admin_user, member_user])
        await session.flush()

        # 2. Create Tenant / Workspace
        tenant = Tenant(
            name="Acme Corporation",
            slug="acme-corp",
            plan="enterprise",
            is_active=True,
        )
        session.add(tenant)
        await session.flush()

        # 3. Create Memberships
        m1 = TenantMember(user_id=owner_user.id, tenant_id=tenant.id, role=TenantRole.OWNER)
        m2 = TenantMember(user_id=admin_user.id, tenant_id=tenant.id, role=TenantRole.ADMIN)
        m3 = TenantMember(user_id=member_user.id, tenant_id=tenant.id, role=TenantRole.MEMBER)
        session.add_all([m1, m2, m3])
        await session.flush()

        # 4. Create Project
        project = Project(
            tenant_id=tenant.id,
            name="Cloud Microservices Migration",
            description="Migrating legacy monolithic monolith to distributed FastAPI services.",
        )
        session.add(project)
        await session.flush()

        # 5. Create Tasks
        t1 = Task(
            tenant_id=tenant.id,
            project_id=project.id,
            assignee_id=member_user.id,
            title="Design Async Database Layer with SQLAlchemy 2.0",
            description="Use asyncsessionmaker and greenlet for non-blocking I/O",
            status=TaskStatus.DONE,
            priority=TaskPriority.HIGH,
        )
        t2 = Task(
            tenant_id=tenant.id,
            project_id=project.id,
            assignee_id=member_user.id,
            title="Implement Multi-Tenant RBAC Dependencies",
            description="Enforce header-based tenant isolation and hierarchy checks",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.URGENT,
        )
        t3 = Task(
            tenant_id=tenant.id,
            project_id=project.id,
            assignee_id=admin_user.id,
            title="Setup Live WebSocket Notification Feeds",
            description="Broadcast task updates to all active workspace members",
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
        )
        session.add_all([t1, t2, t3])

        # 6. Audit Logs
        session.add_all([
            AuditLog(
                tenant_id=tenant.id,
                user_id=owner_user.id,
                action="workspace.created",
                entity_type="tenant",
                entity_id=tenant.id,
                details="Acme Corporation workspace created with Enterprise plan",
            ),
            AuditLog(
                tenant_id=tenant.id,
                user_id=admin_user.id,
                action="project.created",
                entity_type="project",
                entity_id=project.id,
                details=f"Project '{project.name}' initialized",
            ),
        ])

        await session.commit()
        logger.info("Demo database seeded successfully!")
        logger.info("Demo credentials created:")
        logger.info("  - Owner:  owner@novapulse.io / Password123!")
        logger.info("  - Admin:  admin@novapulse.io / Password123!")
        logger.info("  - Member: dev@novapulse.io   / Password123!")


if __name__ == "__main__":
    asyncio.run(seed_data())
