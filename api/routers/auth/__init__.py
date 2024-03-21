import logging
import os
import sys
import uuid
from datetime import timedelta

import sqlalchemy
from azure.communication.email import EmailClient
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt, JWTError
from sqlalchemy import select, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import JSONResponse

import orm
from api.routers.auth.google import google_oauth
from api.routers.utils.security import create_access_token
from api.schemas.user import UserRegistrationSchema, ForgotPasswordSchema, \
    ResetPasswordSchema
from api.schemas.user import UserResponseSchema
from api.utils.security import oauth2_scheme, verify_password, get_password_hash
from app.settings import settings
from orm.models.user import User
from orm.session_manager import get_session as get_db

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logging.basicConfig(filename="user.log", level=logging.DEBUG)
logger.addHandler(handler)  # Define in your .env file
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

router = APIRouter()


def verify_access_token(token: str = Depends(oauth2_scheme)) -> str:
    """
    Verify the access token and return the username if valid.

    This function verifies the validity of an access token and returns the associated username if the token is valid.

    **Parameters:**
    - `token` (str, optional): The access token to be verified. Defaults to `Depends(oauth2_scheme)`.

    **Returns:**
    - `str`: The username associated with the valid access token.

    **Raises:**
    - `HTTPException`: If the access token is invalid or cannot be validated (status code 401).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        # Token is valid, return the username
        return username
    except JWTError as exc:
        raise credentials_exception from exc


@router.post("/register")
async def register_user(user: UserRegistrationSchema, db: AsyncSession = Depends(get_db)) -> UserResponseSchema:
    """
    Register a new user and send verification email.

    This endpoint allows users to register by providing their username, email, and password. It also sends a verification email to the user's email address.

    **Parameters:**
    - `user` (UserRegistrationSchema): The user registration details.
        - `username` (str): The username of the user.
        - `email` (EmailStr): The email address of the user.
        - `password` (str): The password of the user.

    **Returns:**
    - `UserResponseSchema`: The registered user details.
        - `id` (UUID): The ID of the registered user.
        - `username` (str): The username of the registered user.
        - `email` (EmailStr): The email address of the registered user.
        - `created_at` (datetime): The date the user was created at

    **Returns:**
    - `JSONResponse`: Known errors raised when trying to register a new user
        - `detail` (str): The details of the error

    **Example Request:**
    ```json
    POST /register
    {
        "username": "john_doe",
        "email": "john@example.com",
        "password": "password123"
    }
    ```

    **Example Response:**
    ```json
    {
        "id": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        "username": "john_doe",
        "email": "john@example.com",
        "created_at": "2024-04-16T12:51:03.755142"
    }
    ```
    """
    try:
        # Hash the password
        hashed_password = get_password_hash(user.password)

        # Check for duplicate username or email
        user_query = select(User).where(or_(User.name == user.username, User.email == user.email))
        duplicated_users = await db.execute(user_query)
        duplicated_user = duplicated_users.first()
        if duplicated_user:
            # If a user with the same username or email already exists, return a 400 status code
            return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": "Username or email already exists"})

        # If no duplicate user is found, proceed with adding the new user
        user_add = orm.User(name=user.username, email=user.email, password=hashed_password)
        db.add(user_add)
        await db.commit()
        await db.refresh(user_add)

        inserted_id = user_add.id

        # Optionally, send an email
        #if user_add.email:
        #    send_email(user.email, user.username)

        user_response = UserResponseSchema(
            id=inserted_id,
            username=user_add.name,
            email=user_add.email,
            created_at=user_add.created_at,
        )

        # Send verification email
        verification_token = create_access_token(data={"sub": user_add.email}, expires_delta=timedelta(days=ACCESS_TOKEN_EXPIRE_MINUTES))
        verification_link = f"{settings.host_url}/verify?access_token={verification_token}"
        send_verification_email(user_add.email, verification_link)

        return user_response

    except sqlalchemy.exc.IntegrityError as e:
        logger.error(f"SQL Integrity error: {e.detail}")
        await db.rollback()
    except SQLAlchemyError as e:
        logger.error(f"SQLAlchemyError: {e.__dict__}")
        await db.rollback()
    except Exception as e:
        logger.error(f"User registration error: {e}")
        await db.rollback()
        return JSONResponse(status_code=500, content={"detail": str(e)})

@router.post("/token", tags=["authentication"])
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """
    Login and generate access token.

    This endpoint allows users to log in and obtain an access token by providing their username and password.

    **Parameters:**
    - `form_data` (OAuth2PasswordRequestForm, optional): The login form data.
        - `username` (str): The username of the user.
        - `password` (str): The password of the user.

    **Returns:**
    - `dict`: The access token details.
        - `access_token` (str): The access token.
        - `refresh_token` (str): The refresh token.
        - `token_type` (str): The type of the token (e.g., "bearer").

    **Raises:**
    - `HTTPException`: If the username or password is incorrect (status code 401).

    **Example Request:**
    ```
    POST /token
    Content-Type: application/x-www-form-urlencoded

    username=john_doe&password=password123
    ```

    **Example Response:**
    ```json
    {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJqb2huX2RvZSIsImV4cCI6MTYyNDg2NDAwMH0.j4bxYxJQJ4WG4z6x4zx4zx4zx4zx4zx4zx4zx4zx4zx",
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJqb2huX2RvZSIsImV4cCI6MTYyNTQ2ODgwMH0.j4bxYxJQJ4WG4z6x4zx4zx4zx4zx4zx4zx4zx4zx4zx",
        "token_type": "bearer"
    }
    ```
    """
    user_q = select(User).where(User.name == form_data.username)
    user = await db.execute(user_q)
    user = user.first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = user[0]

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email address not verified. Please check your email to verify your account before logging in",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email address not verified. Please check your email to verify your account before logging in",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.name}, expires_delta=access_token_expires)
    refresh_token = create_access_token(data={"sub": user.name}, expires_delta=timedelta(days=7))

    user.refresh_token = refresh_token

    try:
        await db.commit()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update refresh token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/refresh_token", tags=["authentication"])
async def refresh_access_token(refresh_token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    """
    Refresh the access token using a refresh token.

    This endpoint allows users to obtain a new access token by providing a valid refresh token.

    **Parameters:**
    - `refresh_token` (str, optional): The refresh token. Defaults to `Depends(oauth2_scheme)`.

    **Returns:**
    - `dict`: The new access token details.
        - `access_token` (str): The new access token.

    **Raises:**
    - `HTTPException`: If the refresh token is invalid or the user is not found (status code 401).

    **Example Request:**
    ```
    POST /refresh_token
    Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJqb2huX2RvZSIsImV4cCI6MTYyNTQ2ODgwMH0.j4bxYxJQJ4WG4z6x4zx4zx4zx4zx4zx4zx4zx4zx4zx
    ```

    **Example Response:**
    ```json
    {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJqb2huX2RvZSIsImV4cCI6MTYyNDg2ODAwMH0.j4bxYxJQJ4WG4z6x4zx4zx4zx4zx4zx4zx4zx4zx4zx"
    }
    ```
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(refresh_token, settings.secret_key, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        print("refresh_token", refresh_token)
        user_q = select(User).where(User.name == username, User.refresh_token == refresh_token)
        user = await db.execute(user_q)
        user = user.first()
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = create_access_token(data={"sub": username}, expires_delta=access_token_expires)
        return {"access_token": new_access_token}
    except JWTError:
        raise credentials_exception


async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    """
    Get the current user based on the provided access token.

    This function retrieves the current user based on the provided access token by decoding the token and querying the database.

    **Parameters:**
    - `token` (str, optional): The access token. Defaults to `Depends(oauth2_scheme)`.
    - `db` (AsyncSession, optional): The database session. Defaults to `Depends(get_db)`.

    **Returns:**
    - `User`: The current user.

    **Raises:**
    - `HTTPException`: If the access token is invalid (status code 400) or the user is not found (status code 404).
    """
    try:
        secret = settings.secret_key
        payload = jwt.decode(token, secret, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=400, detail="Invalid JWT: user_id missing")

        user_q = select(User).where(User.name == username)
        user = await db.execute(user_q)
        user = user.first()[0]

        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")


@router.get('/google/login')
async def login_google(request: Request):
    """
    Initiate the Google OAuth login process.

    This endpoint initiates the Google OAuth login process by redirecting the user to the Google OAuth authorization page.

    **Parameters:**
    - `request` (Request): The request object.

    **Returns:**
    - `RedirectResponse`: The redirect response to the Google OAuth authorization page.
    """
    redirect_uri = request.url_for('auth_google')
    return await google_oauth.authorize_redirect(request, redirect_uri)


@router.get('/google')
async def auth_google(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Complete the Google OAuth login process.

    This endpoint completes the Google OAuth login process by exchanging the authorization code for access tokens and creating or authenticating the user.

    **Parameters:**
    - `request` (Request): The request object.

    **Returns:**
    - `dict`: The access token details.
        - `access_token` (str): The access token.
        - `refresh_token` (str): The refresh token.
        - `token_type` (str): The type of the token (e.g., "bearer").

    **Raises:**
    - `HTTPException`: If an error occurs during the Google OAuth process (status code 400).
    """
    try:
        token = await google_oauth.authorize_access_token(request)

        user_info = token.get('userinfo')

        user_q = select(User).where(User.email == user_info["email"])
        user = await db.execute(user_q)
        user = user.first()

        if user:
            return JSONResponse(status_code=status.HTTP_200_OK, content={"detail": "Email already registered"})


        user_data = {
            "name": user_info["email"],
            "email": user_info["email"],
            "source": "google"
        }

        user_add = User(name=user_data["email"], email=user_data["email"], source="google")
        db.add(user_add)
        await db.commit()
        await db.refresh(user_add)


        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(data={"sub": user_add.name}, expires_delta=access_token_expires)
        refresh_token = create_access_token(data={"sub": user_add.name}, expires_delta=timedelta(days=7))

        user_add.refresh_token = refresh_token

        await db.commit()

        return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def send_email(recipient_email: str, reset_link: str):
    """
    Email the user.

    This function sends an email to the specified recipient email address with the provided reset link.

    **Parameters:**
    - `recipient_email` (str): The email address of the recipient.
    - `reset_link` (str): The password reset link to be included in the email.

    **Raises:**
    - `Exception`: If an error occurs while sending the email.
    """

    # This assumes you have 'AZURE_COMMUNICATION_SERVICE_CONNECTION_STRING' in your environment variables
    connection_string = os.getenv('AZURE_COMMUNICATION_SERVICE_CONNECTION_STRING')
    try:
        client = EmailClient.from_connection_string(connection_string)

        message = {
            "senderAddress": "DoNotReply@e156441a-cd79-4c6f-9a10-f74ceba5d9af.azurecomm.net",
            "recipients":  {
                "to": [{"address": recipient_email }],
            },
            "content": {
                "subject": "Reset your password",
                "plainText": reset_link,
            }
        }

        poller = client.begin_send(message)
        result = poller.result()

    except Exception as ex:
        print(ex)


@router.post("/forgot_password")
async def forgot_password(email: ForgotPasswordSchema, db: AsyncSession = Depends(get_db)):
    """
    Initiate the password reset process.

    This endpoint initiates the password reset process by sending a password reset link to the user's email.

    **Parameters:**
    - `email` (ForgotPasswordSchema): The email address of the user requesting a password reset.
        - `email` (EmailStr): The email address of the user.

    **Returns:**
    - `dict`: A message indicating that password reset instructions have been sent.
        - `message` (str): The message indicating that password reset instructions have been sent.

    **Raises:**
    - `HTTPException`: If the user is not found with the provided email (status code 404).

    **Example Request:**
    ```json
    POST /forgot_password
    {
        "email": "john@example.com"
    }
    ```

    **Example Response:**
    ```json
    {
        "message": "Password reset instructions sent to your email"
    }
    ```
    """
    try:
        user_q = select(User).where(User.email == email.email)
        user = await db.execute(user_q)
        user = user.first()[0]
        host_url = settings.host_url

        if not user:
            raise HTTPException(status_code=404, detail="User not found with that email")

        reset_token = str(uuid.uuid4())
        user.reset_token = reset_token
        await db.commit()

        reset_link = f"{host_url}/reset_password?token={reset_token}"
        send_email(user.email, reset_link)

        return {"message": "Password reset instructions sent to your email"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=404, detail="User not found with that email")


@router.post("/reset_password")
async def reset_password(data: ResetPasswordSchema, db: AsyncSession = Depends(get_db)):
    """
    Reset the user's password.

    This endpoint allows users to reset their password by providing a valid reset token and a new password.

    **Parameters:**
    - `data` (ResetPasswordSchema): The password reset data.
        - `token` (str): The password reset token.
        - `new_password` (str): The new password.

    **Returns:**
    - `dict`: A message indicating that the password has been reset successfully.
        - `message` (str): The message indicating that the password has been reset successfully.

    **Raises:**
    - `HTTPException`: If the reset token is invalid or expired (status code 400), or if an error occurs during password reset (status code 500).

    **Example Request:**
    ```json
    POST /reset_password
    {
        "token": "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11",
        "new_password": "newPassword123"
    }
    ```

    **Example Response:**
    ```json
    {
        "message": "Password reset successfully"
    }
    ```
    """
    try:
        user_q = select(User).where(User.reset_token == data.token)
        user = await db.execute(user_q)
        user = user.first()[0]

        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")

        hashed_password = get_password_hash(data.new_password)
        user.password = hashed_password
        await db.commit()

        return {"message": "Password reset successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Failed to update password")
