from fastapi import FastAPI, Depends, HTTPException
import models
from db import engine, SessionLocal
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from auth import decode_current_user, get_user_exception


class Todo(BaseModel):
    title: str
    description: str | None
    priority: int = Field(gt=0, lt=6, description="Priority must be between 1 and 5")
    complete: bool


app = FastAPI()
models.Base.metadata.create_all(bind=engine)


def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


@app.get("/")
async def read_all(db: Session = Depends(get_db)):
    return db.query(models.Todos).all()


@app.get("/todos/user")
async def read_all_by_user(
    user: dict = Depends(decode_current_user), db: Session = Depends(get_db)
):
    if user is None:
        raise get_user_exception()
    return db.query(models.Todos).filter(models.Todos.owner_id == user.get("id")).all()


@app.get("/todo/{todo_id}")
async def read_todo(todo_id: int, db: Session = Depends(get_db)):
    todo_model = db.query(models.Todos).filter(models.Todos.id == todo_id).first()
    if todo_model is not None:
        return todo_model
    else:
        raise HTTPException(status_code=404, detail="Item not found")


@app.post("/")
async def create_todo(
    todo: Todo, db: Session = Depends(get_db), user: dict = Depends(decode_current_user)
):
    if user is None:
        raise get_user_exception()

    todo_model = models.Todos()
    todo_model.title = todo.title
    todo_model.description = todo.description
    todo_model.priority = todo.priority
    todo_model.complete = todo.complete
    todo_model.owner_id = user.get("id")

    db.add(todo_model)
    db.commit()
    return {"status_code": 201, "detail": "Successful."}


@app.put("/{todo_id}")
async def update_todo(
    todo_id: int,
    todo: Todo,
    db: Session = Depends(get_db),
    user: dict = Depends(decode_current_user),
):
    if user is None:
        raise get_user_exception()

    todo_model = (
        db.query(models.Todos)
        .filter(models.Todos.id == todo_id)
        .filter(models.Todos.owner_id == user.get("id"))
        .first()
    )

    if todo_model is None:
        raise HTTPException(status_code=404, detail="Not found!")

    todo_model.title = todo.title
    todo_model.description = todo.description
    todo_model.priority = todo.priority
    todo_model.complete = todo.complete

    db.add(todo_model)
    db.commit()

    return {"status_code": 200, "detail": "Successful."}


@app.delete("/{todo_id}", status_code=202)
async def delete_todo(
    todo_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(decode_current_user),
):
    if user is None:
        raise get_user_exception()

    todo_model = (
        db.query(models.Todos)
        .filter(models.Todos.id == todo_id)
        .filter(models.Todos.owner_id == user.get("id"))
        .first()
    )
    if todo_model is None:
        raise HTTPException(status_code=404, detail="Not found!")
    db.delete(todo_model)
    db.commit()
    return {"detail": f"Item {todo_id} successful deleted."}


@app.get("/todo/{todo_id}")
async def read_todo(
    todo_id: int,
    user: dict = Depends(decode_current_user),
    db: Session = Depends(get_db),
):
    if user is None:
        raise get_user_exception()

    todo_model = (
        db.query(models.Todos)
        .filter(models.Todos.id == todo_id)
        .filter(models.Todos.owner_id == user.get("id"))
        .first()
    )

    if todo_model is not None:
        return todo_model

    raise HTTPException(status_code=404, detail="Not found!")
