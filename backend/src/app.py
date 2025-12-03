"""
TaskFlow Backend - FastAPI Task Management Service

A RESTful API for task management with TDD approach.

TP 1 & 2: Uses in-memory storage for simplicity
TP 3: Will introduce PostgreSQL database (see migration guide)
"""

from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import logging

#Nouveaux imports 
from contextlib import asynccontextmanager
import uuid
from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from .database import get_db, init_db
from .models import TaskModel, TaskStatus, TaskPriority

from fastapi.middleware.cors import CORSMiddleware
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("taskflow")


# =============================================================================
# ENUMS & MODELS
# =============================================================================

'''class TaskStatus(str, Enum):
    """Task status enum - simpler than SQLAlchemy version."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"'''


'''class TaskPriority(str, Enum):
    """Task priority enum - simpler than SQLAlchemy version."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"'''


class TaskCreate(BaseModel):
    """Model for creating a new task."""
    title: str = Field(..., min_length=1, max_length=200, description="Task title")
    description: Optional[str] = Field(None, max_length=1000, description="Task description")
    status: TaskStatus = Field(default=TaskStatus.TODO, description="Task status")
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, description="Task priority")
    assignee: Optional[str] = Field(None, max_length=100, description="Assigned user")
    due_date: Optional[datetime] = Field(None, description="Due date")


class TaskUpdate(BaseModel):
    """Model for updating a task - all fields optional for partial updates."""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    assignee: Optional[str] = Field(None, max_length=100)
    due_date: Optional[datetime] = None


# ✅ APRÈS (compatible SQLAlchemy)
class Task(BaseModel):
    """Model for task response."""
    id: str  # ← Changé en str pour UUID
    title: str
    description: Optional[str] = None
    status: TaskStatus
    priority: TaskPriority
    assignee: Optional[str] = None
    due_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Permet la conversion depuis SQLAlchemy


# =============================================================================
# IN-MEMORY STORAGE (for Atelier 1 & 2)
# =============================================================================

# Simple dictionary to store tasks
# In Atelier 3, this will be replaced with PostgreSQL database
'''tasks_db: Dict[int, Task] = {}
next_id = 1'''


'''def get_next_id() -> int:
    """Get next available task ID."""
    global next_id
    current_id = next_id
    next_id += 1
    return current_id'''


'''def clear_tasks():
    """Clear all tasks - useful for testing."""
    global tasks_db, next_id
    tasks_db = {}
    next_id = 1'''


# =============================================================================
# FASTAPI APP
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager - initialise la DB au démarrage."""
    logger.info("🚀 TaskFlow backend starting up...")
    init_db()  # Crée les tables
    logger.info("✅ Database initialized")
    yield
    logger.info("🛑 TaskFlow backend shutting down...")



app = FastAPI(
    title="TaskFlow API",
    description="Simple task management API for learning unit testing and CI/CD",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configuration CORS pour le frontend
cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

'''@app.on_event("startup")
def startup():
    """Simple startup - just log a message."""
    logger.info("🚀 TaskFlow backend starting up...")
    logger.info("Using in-memory storage (no database)")'''


'''@app.on_event("shutdown")
def shutdown():
    """Simple shutdown - just log a message."""
    logger.info("🛑 TaskFlow backend shutting down...")
'''

# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "message": "Welcome to TaskFlow API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check with database status."""
    try:
        db.execute(text("SELECT 1"))
        tasks_count = db.query(TaskModel).count()
        return {
            "status": "healthy",
            "database": "connected",
            "tasks_count": tasks_count
        }
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}


@app.get("/tasks", response_model=List[Task])
async def get_tasks(
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None,
    assignee: Optional[str] = None,
    db: Session = Depends(get_db)  # ← Toujours en dernier dans les paramètres
):
    """Get all tasks with optional filtering."""
    query = db.query(TaskModel)

    if status:
        query = query.filter(TaskModel.status == status)
    if priority:
        query = query.filter(TaskModel.priority == priority)
    if assignee:
        query = query.filter(TaskModel.assignee == assignee)

    return query.all()


@app.get("/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str,db: Session = Depends(get_db)) -> TaskModel:
    """Get a single task by ID."""
    query= db.query(TaskModel).filter(TaskModel.id == task_id)
    task = query.first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


@app.post("/tasks", response_model=Task, status_code=201)
async def create_task(task_data: TaskCreate,db: Session = Depends(get_db)) -> TaskModel:
    """Create a new task."""
    # Validate title is not empty
    if not task_data.title:
        raise HTTPException(status_code=422, detail="Title cannot be empty")
    new_task = TaskModel(
        id=str(uuid.uuid4()),  # Générer un UUID pour l'ID
        title=task_data.title,
        description=task_data.description,
        status=task_data.status,
        priority=task_data.priority,
        assignee=task_data.assignee,
        due_date=task_data.due_date
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return new_task


@app.put("/tasks/{task_id}", response_model=Task)
async def update_task(task_id: str, updates: TaskUpdate, db: Session = Depends(get_db)) -> TaskModel:
    """
    Update an existing task (partial update supported).

    TODO (Atelier 1 - Exercice 2): Implémenter cette fonction

    Étapes à suivre:
    1. Vérifier que la tâche existe dans tasks_db
       - Si elle n'existe pas, lever HTTPException(status_code=404, detail=f"Task {task_id} not found")

    2. Récupérer la tâche existante

    3. Extraire les champs à mettre à jour avec updates.model_dump(exclude_unset=True)

    4. Valider le titre s'il est fourni (ne doit pas être vide)
       - Si vide, lever HTTPException(status_code=422, detail="Title cannot be empty")

    5. Créer une nouvelle Task avec:
       - Les champs mis à jour (utiliser update_data.get("field", existing_task.field))
       - created_at = existing_task.created_at (ne change pas)
       - updated_at = datetime.utcnow() (nouvelle date)

    6. Mettre à jour tasks_db[task_id]

    7. Retourner la tâche mise à jour

    Indice: Regardez comment create_task fonctionne pour vous inspirer
    """
    # TODO: Votre code ici
    query= db.query(TaskModel).filter(TaskModel.id == task_id)
    existing_task = query.first()
    if not existing_task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    update_data = updates.model_dump(exclude_unset=True)
    if "title" in update_data and not update_data["title"]:
        raise HTTPException(status_code=422, detail="Title cannot be empty")
    for key, value in update_data.items():
        setattr(existing_task, key, value)
    existing_task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(existing_task)
    return existing_task

@app.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: str,db: Session = Depends(get_db)):
    """
    Delete a task by ID.

    TODO (Atelier 1 - Exercice 1): Implémenter cette fonction

    Étapes à suivre:
    1. Vérifier que la tâche existe dans tasks_db
       - Si elle n'existe pas, lever HTTPException(status_code=404, detail=f"Task {task_id} not found")

    2. Supprimer la tâche du dictionnaire tasks_db
       - Utiliser: del tasks_db[task_id]

    3. Retourner None (car status_code=204 n'a pas de body)

    Indice: C'est très simple, seulement 3 lignes de code !
    """
    # TODO: Votre code ici
    query= db.query(TaskModel).filter(TaskModel.id == task_id)
    existing_task = query.first()
    if not existing_task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    db.delete(existing_task)
    db.commit()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)