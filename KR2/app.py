from fastapi import FastAPI, HTTPException, Response, Cookie
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
import uuid
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
import time
from datetime import datetime
import re

app = FastAPI(title="Server Applications Development", version="1.0")


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    age: Optional[int] = Field(None, ge=0, le=150)
    is_subscribed: Optional[bool] = Field(False)

    @field_validator('age')
    def validate_age(cls, v):
        if v is not None and v < 0:
            raise ValueError('Возраст должен быть положительным числом')
        return v


@app.post("/create_user")
async def create_user(user: UserCreate):
    return user.model_dump()


sample_products = [
    {"product_id": 123, "name": "Smartphone", "category": "Electronics", "price": 60000},
    {"product_id": 456, "name": "Phone Case", "category": "Accessories", "price": 2000},
    {"product_id": 789, "name": "Iphone", "category": "Electronics", "price": 130000},
    {"product_id": 101, "name": "Headphones", "category": "Accessories", "price": 10000},
    {"product_id": 202, "name": "Smartwatch", "category": "Electronics", "price": 30000}
]


@app.get("/product/{product_id}")
async def get_product(product_id: int):
    for product in sample_products:
        if product["product_id"] == product_id:
            return product
    raise HTTPException(status_code=404, detail="Product not found")


@app.get("/products/search")
async def search_products(
        keyword: str,
        category: Optional[str] = None,
        limit: int = 10
):
    results = []
    keyword_lower = keyword.lower()

    for product in sample_products:
        if keyword_lower in product["name"].lower():
            if category is None or product["category"].lower() == category.lower():
                results.append(product)

    return results[:limit]


sessions = {}


@app.post("/login")
async def login(username: str, password: str):
    if username == "user123" and password == "password123":
        session_token = str(uuid.uuid4())
        sessions[session_token] = username

        response = JSONResponse({"message": "Login successful"})
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            max_age=3600
        )
        return response

    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/user")
async def get_user(session_token: Optional[str] = Cookie(None)):
    if not session_token or session_token not in sessions:
        raise HTTPException(status_code=401, detail="Unauthorized")

    return {"username": sessions[session_token], "message": "Profile information"}


SECRET_KEY = "your-secret-key-here"
serializer = URLSafeTimedSerializer(SECRET_KEY)

users_db = {
    "user123": {"password": "password123", "user_id": str(uuid.uuid4())}
}


@app.post("/login_signed")
async def login_signed(username: str, password: str):
    if username in users_db and users_db[username]["password"] == password:
        user_id = users_db[username]["user_id"]
        session_token = serializer.dumps(user_id)

        response = JSONResponse({"message": "Login successful"})
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            max_age=300
        )
        return response

    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.get("/profile_signed")
async def get_profile_signed(session_token: Optional[str] = Cookie(None)):
    if not session_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        user_id = serializer.loads(session_token, max_age=300)

        username = None
        for name, data in users_db.items():
            if data["user_id"] == user_id:
                username = name
                break

        if username:
            return {"username": username, "user_id": user_id}

    except SignatureExpired:
        raise HTTPException(status_code=401, detail="Session expired")
    except BadSignature:
        raise HTTPException(status_code=401, detail="Invalid session")

    raise HTTPException(status_code=401, detail="Unauthorized")


sessions_dynamic = {}


@app.post("/login_dynamic")
async def login_dynamic(username: str, password: str):
    if username in users_db and users_db[username]["password"] == password:
        user_id = users_db[username]["user_id"]
        current_timestamp = int(time.time())

        data = f"{user_id}.{current_timestamp}"
        signature = serializer.dumps(data)

        sessions_dynamic[user_id] = current_timestamp

        response = JSONResponse({"message": "Login successful"})
        response.set_cookie(
            key="session_token",
            value=signature,
            httponly=True,
            max_age=300
        )
        return response

    raise HTTPException(status_code=401, detail="Invalid credentials")


def verify_dynamic_session(session_token: Optional[str]):
    if not session_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        data = serializer.loads(session_token, max_age=300)
        parts = data.split('.')
        if len(parts) != 2:
            raise HTTPException(status_code=401, detail="Invalid session")

        user_id = parts[0]
        timestamp = int(parts[1])

        if user_id not in sessions_dynamic:
            raise HTTPException(status_code=401, detail="Invalid session")

        current_time = int(time.time())
        last_activity = sessions_dynamic.get(user_id, 0)

        if timestamp != last_activity:
            raise HTTPException(status_code=401, detail="Invalid session")

        return user_id, timestamp

    except SignatureExpired:
        raise HTTPException(status_code=401, detail="Session expired")
    except (BadSignature, ValueError, IndexError):
        raise HTTPException(status_code=401, detail="Invalid session")


@app.get("/profile_dynamic")
async def get_profile_dynamic(
        response: Response,
        session_token: Optional[str] = Cookie(None)
):
    user_id, timestamp = verify_dynamic_session(session_token)
    current_time = int(time.time())
    time_since_last_activity = current_time - timestamp

    if time_since_last_activity > 300:
        raise HTTPException(status_code=401, detail="Session expired")

    if 180 <= time_since_last_activity < 300:
        new_timestamp = current_time
        sessions_dynamic[user_id] = new_timestamp

        new_data = f"{user_id}.{new_timestamp}"
        new_signature = serializer.dumps(new_data)
        response.set_cookie(
            key="session_token",
            value=new_signature,
            httponly=True,
            max_age=300
        )

    username = None
    for name, data in users_db.items():
        if data["user_id"] == user_id:
            username = name
            break

    return {"username": username, "user_id": user_id}


class CommonHeaders(BaseModel):
    user_agent: str = Field(..., alias="User-Agent")
    accept_language: str = Field(..., alias="Accept-Language")

    @field_validator('accept_language')
    def validate_accept_language(cls, v):
        pattern = r'^([a-z]{2}(-[A-Z]{2})?(;q=[0-9]\.[0-9])?)(,[a-z]{2}(-[A-Z]{2})?(;q=[0-9]\.[0-9])?)*$'
        if not re.match(pattern, v):
            raise ValueError('Invalid Accept-Language format')
        return v

    class Config:
        populate_by_name = True


@app.get("/headers")
async def get_headers(headers: CommonHeaders):
    return {
        "User-Agent": headers.user_agent,
        "Accept-Language": headers.accept_language
    }


@app.get("/info")
async def get_info(
        response: Response,
        headers: CommonHeaders
):
    current_time = datetime.now().isoformat()
    response.headers["X-Server-Time"] = current_time

    return {
        "message": "Добро пожаловать! Ваши заголовки успешно обработаны.",
        "headers": {
            "User-Agent": headers.user_agent,
            "Accept-Language": headers.accept_language
        }
    }


@app.get("/")
async def root():
    return {
        "message": "FastAPI Server Applications Development",
        "endpoints": {
            "3.1 - Create User": "POST /create_user",
            "3.2 - Get Product": "GET /product/{product_id}",
            "3.2 - Search Products": "GET /products/search",
            "5.1 - Login": "POST /login",
            "5.1 - User Profile": "GET /user",
            "5.2 - Login (signed)": "POST /login_signed",
            "5.2 - Profile (signed)": "GET /profile_signed",
            "5.3 - Login (dynamic)": "POST /login_dynamic",
            "5.3 - Profile (dynamic)": "GET /profile_dynamic",
            "5.4 - Headers": "GET /headers",
            "5.4 - Info": "GET /info"
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
