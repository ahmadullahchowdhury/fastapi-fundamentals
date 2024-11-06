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
# Middleware for request timing
@app.middleware("http")
async def add_process_time_header(request, call_next):
    import time
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    print(f"Request to {request.url.path} took {process_time} seconds")
    return response

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
from fastapi import Request
from fastapi.responses import JSONResponse
import time

requests = {}
RATE_LIMIT = 5  # requests
RATE_TIME = 10  # seconds

@app.middleware("http")
async def rate_limit(request: Request, call_next):
    client_ip = request.client.host
    if client_ip in requests:
        if len(requests[client_ip]) >= RATE_LIMIT:
            # Remove old requests
            current_time = time.time()
            requests[client_ip] = [req_time for req_time in requests[client_ip] 
                                 if current_time - req_time < RATE_TIME]
            if len(requests[client_ip]) >= RATE_LIMIT:
                return JSONResponse(
                    status_code=429,
                    content={"message": "Too many requests"}
                )
    else:
        requests[client_ip] = []
    
    requests[client_ip].append(time.time())
    response = await call_next(request)
    return response

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






    