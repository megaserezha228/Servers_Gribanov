from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
import models
from typing import List

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Добро пожаловать в моё приложение FastAPI!"}

@app.get("/html", response_class=HTMLResponse)
async def get_html():
    return FileResponse("index.html")

user = models.User(name="Иван Петров", id=1)

@app.get("/users")
async def get_user():
    return JSONResponse(content=user.model_dump())

feedbacks: List[models.Feedback] = []

@app.post("/feedback")
async def create_feedback(feedback: models.Feedback):
    feedbacks.append(feedback)
    return {
        "message": f"Feedback received. Thank you, {feedback.name}."
    }

@app.get("/feedbacks")
async def get_all_feedbacks():
    return {"feedbacks": [f.model_dump() for f in feedbacks]}

@app.get("/calculate")
async def calculate(num1: int, num2: int):
    return {"result": num1 + num2}