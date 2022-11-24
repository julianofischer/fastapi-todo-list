from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db import SessionLocal, engine
import models
import hashlib
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from datetime import datetime, timedelta
from jose import jwt, JWTError, ExpiredSignatureError

SECRET_KEY = "not so secret"
ALGO = "HS256"


class CreateUser(BaseModel):
    username: str
    email: str | None
    first_name: str
    last_name: str
    password: str

oauth2_bearer = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI()

def get_pwd_hash(pwd):
    encoded_pwd = pwd.encode("utf-8")
    return hashlib.sha256(encoded_pwd).hexdigest()


def verify_password(plain_password, hashed_password):
    hashed_password1 = get_pwd_hash(plain_password)
    return hashed_password1 == hashed_password


def authenticate_user(username: str, password: str, db):
    user = db.query(models.User).filter(models.User.username==username).first()

    if not user:
        return False

    if verify_password(password, user.hashed_password):
        return user
    return False


def create_access_token(username: str, user_id: int, expires_delta: timedelta | None):
    encode = {"sub": username, "id": user_id}
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    encode.update({"exp": expire})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGO)


def decode_current_user(token: str = Depends(oauth2_bearer)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGO])
        username: str = payload.get("sub")
        user_id: int = payload.get("id")
        if username is None or user_id is None:
            raise get_user_exception()
        return {
            "username": username,
            "id": user_id,
        }
    except ExpiredSignatureError:
        raise HTTPException(status_code=403, detail="token has been expired")
    except JWTError:
        raise get_user_exception()


def get_user_exception():
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not auth user",
        headers={"WWW-Authenticate": "Bearer"}
    )
    return credentials_exception


def get_token_exception():
    token_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"}
    )
    return token_exception

def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()
        

@app.post("/create/user")
async def create_new_user(user: CreateUser, db: Session = Depends(get_db)):
    user_model = models.User()
    user_model.email = user.email
    user_model.username = user.username
    user_model.first_name = user.first_name
    user_model.last_name = user.last_name
    user_model.hashed_password = get_pwd_hash(user.password)
    user_model.is_active = True
    db.add(user_model)
    db.commit()
    return user_model


@app.post("/token")
async def login_for_acess_token(form_data: OAuth2PasswordRequestForm = Depends(),
                                db: Session = Depends(get_db)):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise get_token_exception()
    
    token_expires = timedelta(minutes=20)
    token = create_access_token(user.username, user.id, token_expires)
    return {
        "status_code": 200,
        "detail": "User validated",
        "token": token
    }