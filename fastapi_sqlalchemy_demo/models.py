from database import Base
from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)

    tasks: Mapped[list["TaskModel"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class TaskModel(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    owner: Mapped["UserModel"] = relationship(back_populates="tasks")
