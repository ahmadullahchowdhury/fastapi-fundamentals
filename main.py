from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from sqlalchemy.sql.expression import select
import models, schemas
from typing import Optional, List

# Create the database tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Custom exception handler
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail, "custom": "error handler"}
    )

# Background tasks
from fastapi import BackgroundTasks
@app.post("/todos/background/")
async def create_todo_background(todo: schemas.TodoCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    def process_todo(todo_data: dict):
        # Simulate long running task
        import time
        time.sleep(2)
        print(f"Processed todo: {todo_data}")
        
    db_todo = models.Todo(**todo.dict())
    db.add(db_todo)
    db.commit()
    db.refresh(db_todo)
    background_tasks.add_task(process_todo, todo.dict())
    return {"message": "Todo created, processing in background"}

# Rate limiting


@app.post("/todos/", response_model=schemas.Todo)
def create_todo(todo: schemas.TodoCreate, db: Session = Depends(get_db)):
     db_todo = models.Todo(**todo.dict())
     db.add(db_todo)
     db.commit()
     db.refresh(db_todo)
     return db_todo

@app.get("/todos/{todo_id}", response_model=schemas.Todo)
def read_todo(todo_id: int, db: Session = Depends(get_db)):
     todo = db.query(models.Todo).filter(models.Todo.id == todo_id).first()
     if not todo:
         raise HTTPException(status_code=404, detail="Todo not found")
     return todo

@app.put("/todos/{todo_id}", response_model=schemas.Todo)
def update_todo(todo_id: int, todo: schemas.TodoCreate, db: Session = Depends(get_db)):
     db_todo = db.query(models.Todo).filter(models.Todo.id == todo_id).first()
     if not db_todo:
         raise HTTPException(status_code=404, detail="Todo not found")
     for key, value in todo.dict().items():
         setattr(db_todo, key, value)
     db.commit()
     db.refresh(db_todo)
     return db_todo

@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: int, db: Session = Depends(get_db)):
     todo = db.query(models.Todo).filter(models.Todo.id == todo_id).first()
     if not todo:
         raise HTTPException(status_code=404, detail="Todo not found")
     db.delete(todo)
     db.commit()
     return {"detail": "Todo deleted"}

@app.get("/todos/", response_model=List[schemas.Todo])
def read_todos(db: Session = Depends(get_db)):
     todos = db.query(models.Todo).all()
     return todos






    