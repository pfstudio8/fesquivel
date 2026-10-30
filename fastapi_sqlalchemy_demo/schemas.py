from pydantic import BaseModel, ConfigDict

# Esquemas para Usuario
class UserBase(BaseModel):
    username: str
    email: str | None = None

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


# Esquemas para Tarea
class TaskBase(BaseModel):
    title: str
    description: str | None = None
    completed: bool = False
    is_archived: bool = False

class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    completed: bool = False

class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    completed: bool | None = None
    is_archived: bool | None = None

class TaskResponse(TaskBase):
    id: int
    user_id: int

    # Configuración para permitir la lectura de modelos ORM directamente
    model_config = ConfigDict(from_attributes=True)
