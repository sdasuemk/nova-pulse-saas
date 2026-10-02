from typing import List, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.exceptions import NotFoundException
from app.models.project import Project, Task, TaskStatus
from app.schemas.project import ProjectCreate, ProjectUpdate, TaskCreate, TaskUpdate


class ProjectService:
    @classmethod
    async def create_project(cls, db: AsyncSession, tenant_id: str, data: ProjectCreate) -> Project:
        project = Project(
            tenant_id=tenant_id,
            name=data.name,
            description=data.description,
        )
        db.add(project)
        await db.flush()
        return project

    @classmethod
    async def list_projects(cls, db: AsyncSession, tenant_id: str) -> List[Project]:
        query = (
            select(Project)
            .where(Project.tenant_id == tenant_id)
            .order_by(Project.created_at.desc())
        )
        res = await db.execute(query)
        return list(res.scalars().all())

    @classmethod
    async def get_project(cls, db: AsyncSession, tenant_id: str, project_id: str) -> Project:
        query = (
            select(Project)
            .options(
                selectinload(Project.tasks).selectinload(Task.assignee)
            )
            .where(and_(Project.id == project_id, Project.tenant_id == tenant_id))
        )
        res = await db.execute(query)
        project = res.scalar_one_or_none()
        if not project:
            raise NotFoundException("Project", project_id)
        return project

    @classmethod
    async def update_project(
        cls, db: AsyncSession, tenant_id: str, project_id: str, data: ProjectUpdate
    ) -> Project:
        project = await cls.get_project(db, tenant_id, project_id)
        if data.name is not None:
            project.name = data.name
        if data.description is not None:
            project.description = data.description

        await db.flush()
        return project

    @classmethod
    async def delete_project(cls, db: AsyncSession, tenant_id: str, project_id: str) -> None:
        project = await cls.get_project(db, tenant_id, project_id)
        await db.delete(project)

    # --- Tasks ---
    @classmethod
    async def create_task(
        cls, db: AsyncSession, tenant_id: str, project_id: str, data: TaskCreate
    ) -> Task:
        # Verify project exists and belongs to this tenant
        await cls.get_project(db, tenant_id, project_id)

        task = Task(
            tenant_id=tenant_id,
            project_id=project_id,
            title=data.title,
            description=data.description,
            status=data.status,
            priority=data.priority,
            assignee_id=data.assignee_id,
        )
        db.add(task)
        await db.flush()
        await db.refresh(task, ["assignee"])
        return task

    @classmethod
    async def list_tasks(
        cls,
        db: AsyncSession,
        tenant_id: str,
        project_id: Optional[str] = None,
        status: Optional[TaskStatus] = None,
    ) -> List[Task]:
        filters = [Task.tenant_id == tenant_id]
        if project_id:
            filters.append(Task.project_id == project_id)
        if status:
            filters.append(Task.status == status)

        query = (
            select(Task)
            .options(selectinload(Task.assignee))
            .where(and_(*filters))
            .order_by(Task.created_at.desc())
        )
        res = await db.execute(query)
        return list(res.scalars().all())

    @classmethod
    async def get_task(cls, db: AsyncSession, tenant_id: str, task_id: str) -> Task:
        query = (
            select(Task)
            .options(selectinload(Task.assignee))
            .where(and_(Task.id == task_id, Task.tenant_id == tenant_id))
        )
        res = await db.execute(query)
        task = res.scalar_one_or_none()
        if not task:
            raise NotFoundException("Task", task_id)
        return task

    @classmethod
    async def update_task(
        cls, db: AsyncSession, tenant_id: str, task_id: str, data: TaskUpdate
    ) -> Task:
        task = await cls.get_task(db, tenant_id, task_id)

        if data.title is not None:
            task.title = data.title
        if data.description is not None:
            task.description = data.description
        if data.status is not None:
            task.status = data.status
        if data.priority is not None:
            task.priority = data.priority
        if data.assignee_id is not None:
            task.assignee_id = data.assignee_id

        await db.flush()
        await db.refresh(task, ["assignee"])
        return task

    @classmethod
    async def delete_task(cls, db: AsyncSession, tenant_id: str, task_id: str) -> None:
        task = await cls.get_task(db, tenant_id, task_id)
        await db.delete(task)
