from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from metadata import SessionDep
from models import User, UserCreate, UserOut, UserLogin, get_current_user, hash_password, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, timedelta, Token
from tests.tasks import send_email_task

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

@router.post("/register/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, session: SessionDep):
    db_user = await session.execute(select(User).where(User.username == user.username))
    if db_user.scalars().first():
        raise HTTPException(status_code=400, detail="Username already registered")
    new_user = User(username=user.username, password=hash_password(user.password))
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    # send_email_task.delay(
    #     recipient=new_user.username,
    #     subject="Welcome to Notes App",
    #     body="Thank you for registering!"
    # )
    return new_user

@router.post("/login/", response_model=Token)
async def login(credentials: UserLogin, session: SessionDep):
    user = await session.execute(select(User).where(User.username == credentials.username))
    user = user.scalars().first()
    if not user or not verify_password(credentials.password, user.password):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user