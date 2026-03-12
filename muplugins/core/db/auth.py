import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pydantic
from asyncpg import Connection
from asyncpg.exceptions import UniqueViolationError
from fastapi import HTTPException, status

from .fields import username
from .users import UserModel


class UserLogin(pydantic.BaseModel):
    username: username
    password: pydantic.SecretStr


class TokenResponse(pydantic.BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

    @classmethod
    def from_str(cls, manager, sub: str) -> "TokenResponse":
        token = manager.create_token(sub)
        refresh = manager.create_refresh(sub)
        return cls(access_token=token, refresh_token=refresh, token_type="bearer")

    @classmethod
    def from_uuid(cls, manager, id: uuid.UUID) -> "TokenResponse":
        sub = str(id)
        return cls.from_str(manager, sub)


class RefreshTokenModel(pydantic.BaseModel):
    refresh_token: str


# meant to be run in a Transaction.
async def register_user(
    conn: Connection, crypt_context, username: str, password: str
) -> UserModel:
    admin_level = 0

    try:
        hashed = crypt_context.hash(password)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Error hashing password."
        )

    # if there are no users, make this user an admin.
    if not (await conn.fetchrow("SELECT id FROM users")):
        admin_level = 10

    try:
        # Insert the new user.
        user_row = await conn.fetchrow(
            """
            INSERT INTO users (username, admin_level)
            VALUES ($1, $2)
            RETURNING *
            """,
            username,
            admin_level,
        )
    except UniqueViolationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already exists.",
        )
    user = UserModel(**user_row)

    # Insert the password record.
    password_row = await conn.fetchrow(
        """
        INSERT INTO passwords (user_id, password_hash)
        VALUES ($1, $2)
        RETURNING id
        """,
        user.id,
        hashed,
    )
    password_id = password_row["id"]

    # Update the user to set the current password.
    await conn.execute(
        "UPDATE users SET current_password_id=$1 WHERE id=$2",
        password_id,
        user.id,
    )
    return user


# Meant to be run in a Transaction.
async def authenticate_user(
    conn: Connection,
    crypt_context,
    username: str,
    password: str,
    ip: str,
    user_agent: str | None,
) -> UserModel:
    # Retrieve the latest password row for this user.
    retrieved_user = await conn.fetchrow(
        """
        SELECT *
        FROM user_passwords
        WHERE username = $1 LIMIT 1
        """,
        username,
    )

    if not retrieved_user:
        raise HTTPException(status_code=400, detail="Invalid credentials.")

    user_id = retrieved_user["id"]

    pass_hash = retrieved_user["password_hash"]

    if not (pass_hash and crypt_context.verify(password, pass_hash)):
        await conn.execute(
            """
            INSERT INTO loginrecords (user_id, ip_address, success, user_agent)
            VALUES ($1, $2, $3, $4)
            """,
            user_id,
            ip,
            False,
            user_agent,
        )
        raise HTTPException(status_code=400, detail="Invalid credentials.")

    if crypt_context.needs_update(pass_hash):
        try:
            hashed = crypt_context.hash(password)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error hashing password.",
            )
        password_row = await conn.fetchrow(
            """
            INSERT INTO passwords (user_id, password_hash)
            VALUES ($1, $2)
            RETURNING id
            """,
            user_id,
            hashed,
        )
        password_id = password_row["id"]

        # Update the user to set the current password.
        await conn.execute(
            "UPDATE users SET current_password_id=$1 WHERE id=$2",
            password_id,
            retrieved_user["id"],
        )

    # Record successful login.
    await conn.execute(
        """
        INSERT INTO loginrecords (user_id, ip_address, success, user_agent)
        VALUES ($1, $2, $3, $4)
        """,
        retrieved_user["id"],
        ip,
        True,
        user_agent,
    )

    return UserModel(**retrieved_user)
