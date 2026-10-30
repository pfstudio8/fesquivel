from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import engine, Base, get_db, AsyncSessionLocal
from models import UserModel, TaskModel
from schemas import TaskCreate, TaskUpdate, TaskResponse, UserResponse

# Evento de inicio y apagado para crear tablas y sembrar el usuario único inicial
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crear tablas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Inicializar el usuario único si no existe
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(UserModel).limit(1))
        user = result.scalars().first()
        if not user:
            default_user = UserModel(
                username="usuario_principal",
                email="usuario@example.com"
            )
            session.add(default_user)
            await session.commit()
    yield

app = FastAPI(
    title="FastAPI con SQLAlchemy 2.0 - Gestión de Tareas",
    description="API para gestión de tareas de usuario único con soporte para completar y archivar/ocultar.",
    version="1.0.0",
    lifespan=lifespan
)

# Dependencia para obtener el usuario único del sistema
async def get_current_user(db: AsyncSession = Depends(get_db)) -> UserModel:
    result = await db.execute(select(UserModel).limit(1))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario único no configurado en el sistema"
        )
    return user


# ==========================================
# Endpoints de Usuario Único
# ==========================================
@app.get("/user/", response_model=UserResponse, summary="Obtener información del usuario único")
async def get_user_profile(current_user: UserModel = Depends(get_current_user)):
    return current_user


# ==========================================
# Endpoints de Tareas
# ==========================================

# 1. Dar de alta una tarea (CREATE)
@app.post("/tasks/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, summary="Dar de alta una tarea")
async def create_task(
    task: TaskCreate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    db_task = TaskModel(
        title=task.title,
        description=task.description,
        completed=task.completed,
        is_archived=False,
        user_id=current_user.id
    )
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task


# 2. Listar Tareas con filtros para ocultar terminadas o archivadas (READ - List)
@app.get("/tasks/", response_model=list[TaskResponse], summary="Listar tareas con opción de ocultar terminadas/archivadas")
async def read_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    hide_completed: bool = Query(False, description="Ocultar tareas marcadas como terminadas"),
    hide_archived: bool = Query(True, description="Ocultar tareas que han sido archivadas"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(TaskModel).where(TaskModel.user_id == current_user.id)
    
    if hide_completed:
        query = query.where(TaskModel.completed == False)
    if hide_archived:
        query = query.where(TaskModel.is_archived == False)

    result = await db.execute(query.offset(skip).limit(limit))
    tasks = result.scalars().all()
    return list(tasks)


# 3. Obtener una Tarea por ID (READ - Detail)
@app.get("/tasks/{task_id}", response_model=TaskResponse, summary="Obtener detalle de una tarea")
async def read_task(
    task_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(TaskModel).where(TaskModel.id == task_id, TaskModel.user_id == current_user.id)
    )
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")
    return task


# 4. Actualizar campos generales de una Tarea (UPDATE)
@app.put("/tasks/{task_id}", response_model=TaskResponse, summary="Actualizar una tarea")
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(TaskModel).where(TaskModel.id == task_id, TaskModel.user_id == current_user.id)
    )
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")

    if task_data.title is not None:
        task.title = task_data.title
    if task_data.description is not None:
        task.description = task_data.description
    if task_data.completed is not None:
        task.completed = task_data.completed
    if task_data.is_archived is not None:
        task.is_archived = task_data.is_archived

    await db.commit()
    await db.refresh(task)
    return task


# 5. Marcar tarea como terminada directamente (COMPLETE)
@app.patch("/tasks/{task_id}/complete", response_model=TaskResponse, summary="Marcar tarea como terminada")
async def complete_task(
    task_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(TaskModel).where(TaskModel.id == task_id, TaskModel.user_id == current_user.id)
    )
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")

    task.completed = True
    await db.commit()
    await db.refresh(task)
    return task


# 6. Desmarcar tarea terminada (UNCOMPLETE)
@app.patch("/tasks/{task_id}/uncomplete", response_model=TaskResponse, summary="Desmarcar tarea como terminada")
async def uncomplete_task(
    task_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(TaskModel).where(TaskModel.id == task_id, TaskModel.user_id == current_user.id)
    )
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")

    task.completed = False
    await db.commit()
    await db.refresh(task)
    return task


# 7. Archivar una tarea (ARCHIVE)
@app.patch("/tasks/{task_id}/archive", response_model=TaskResponse, summary="Archivar una tarea")
async def archive_task(
    task_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(TaskModel).where(TaskModel.id == task_id, TaskModel.user_id == current_user.id)
    )
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")

    task.is_archived = True
    await db.commit()
    await db.refresh(task)
    return task


# 8. Desarchivar una tarea (UNARCHIVE)
@app.patch("/tasks/{task_id}/unarchive", response_model=TaskResponse, summary="Desarchivar una tarea")
async def unarchive_task(
    task_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(TaskModel).where(TaskModel.id == task_id, TaskModel.user_id == current_user.id)
    )
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")

    task.is_archived = False
    await db.commit()
    await db.refresh(task)
    return task


# 9. Archivar todas las tareas terminadas (ARCHIVE COMPLETED)
@app.post("/tasks/archive-completed", summary="Archivar en lote todas las tareas terminadas")
async def archive_completed_tasks(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(TaskModel).where(
            TaskModel.user_id == current_user.id,
            TaskModel.completed == True,
            TaskModel.is_archived == False
        )
    )
    tasks = result.scalars().all()
    for task in tasks:
        task.is_archived = True
    
    await db.commit()
    return {"message": f"Se archivaron {len(tasks)} tareas finalizadas"}


# 10. Eliminar una Tarea (DELETE)
@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar una tarea")
async def delete_task(
    task_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(TaskModel).where(TaskModel.id == task_id, TaskModel.user_id == current_user.id)
    )
    task = result.scalars().first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarea no encontrada")

    await db.delete(task)
    await db.commit()
    return None
