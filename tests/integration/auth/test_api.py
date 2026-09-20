import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, hash_password
from app.features.auth.models import User


@pytest.mark.asyncio
async def test_register_success(client):
    user_data = {
        "email": "api-register@example.com",
        "password": "StrongPassword123",
    }
    response = await client.post(
        "/auth/register",
        json=user_data,
    )
    data = response.json()
    assert response.status_code == 200
    assert data["email"] == user_data["email"]
    assert data["is_active"] is True
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    user_data = {
        "email": "api-register_test@example.com",
        "password": "StrongPassword123",
    }

    response = await client.post(
        "/auth/register",
        json=user_data,
    )

    response_2 = await client.post(
        "/auth/register",
        json=user_data,
    )
    assert response.status_code == 200
    assert response_2.status_code == 409
    assert response_2.json()["detail"] == "Email already registered"


@pytest.mark.asyncio
async def test_register_invalid_email(client):
    user_data = {
        "email": "not-an-email",
        "password": "StrongPassword123",
    }

    response = await client.post(
        "/auth/register",
        json=user_data,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_password_too_short(client):
    user_data = {
        "email": "api-register-short-password@example.com",
        "password": "1234567",
    }

    response = await client.post(
        "/auth/register",
        json=user_data,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_password_too_long(client):
    user_data = {
        "email": "api-register-long-password@example.com",
        "password": "a" * 129,
    }

    response = await client.post(
        "/auth/register",
        json=user_data,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_missing_email(client):
    user_data = {
        "password": "StrongPassword123",
    }

    response = await client.post(
        "/auth/register",
        json=user_data,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_missing_password(client):
    user_data = {
        "email": "api-register-missing-password@example.com",
    }

    response = await client.post(
        "/auth/register",
        json=user_data,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client):
    user_data = {
        "email": "api-login@example.com",
        "password": "StrongPassword123",
    }

    register_response = await client.post(
        "/auth/register",
        json=user_data,
    )
    login_response = await client.post(
        "/auth/login",
        json=user_data,
    )

    assert register_response.status_code == 200
    assert login_response.status_code == 200
    login_data = login_response.json()
    assert login_data["refresh_token"]
    assert login_data["access_token"]
    assert login_data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_user_not_found(client):
    user_data = {
        "email": "api-login-not-found@example.com",
        "password": "StrongPassword123",
    }

    response = await client.post(
        "/auth/login",
        json=user_data,
    )
    data = response.json()

    assert response.status_code == 401
    assert data["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    user_data = {
        "email": "api-login-wrong-password@example.com",
        "password": "StrongPassword123",
    }

    register_response = await client.post(
        "/auth/register",
        json=user_data,
    )

    wrong_password_data = {
        "email": user_data["email"],
        "password": "WrongPassword123",
    }

    login_response = await client.post(
        "/auth/login",
        json=wrong_password_data,
    )
    data = login_response.json()

    assert register_response.status_code == 200
    assert login_response.status_code == 401
    assert data["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_invalid_email(client):
    user_data = {
        "email": "not-an-email",
        "password": "StrongPassword123",
    }

    response = await client.post(
        "/auth/login",
        json=user_data,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_password_too_short(client):
    user_data = {
        "email": "api-login-short-password@example.com",
        "password": "1234567",
    }

    response = await client.post(
        "/auth/login",
        json=user_data,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_missing_password(client):
    user_data = {
        "email": "api-login-missing-password@example.com",
    }

    response = await client.post(
        "/auth/login",
        json=user_data,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_inactive_user(
    client,
    db_session,
):
    user = User(
        email="inactive@example.com",
        password_hash=hash_password("password123"),
        is_active=False,
    )

    db_session.add(user)
    await db_session.commit()

    response = await client.post(
        "/auth/login",
        json={
            "email": "inactive@example.com",
            "password": "password123",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_refresh_success(client):
    user_data = {
        "email": "api-refresh@example.com",
        "password": "StrongPassword123",
    }

    register_response = await client.post(
        "/auth/register",
        json=user_data,
    )

    login_response = await client.post(
        "/auth/login",
        json=user_data,
    )

    login_data = login_response.json()
    refresh_token = login_data["refresh_token"]

    refresh_response = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )
    assert register_response.status_code == 200
    assert login_response.status_code == 200
    assert refresh_response.status_code == 200
    refresh_data = refresh_response.json()
    assert refresh_data["refresh_token"]
    assert refresh_data["access_token"]
    assert refresh_data["token_type"] == "bearer"
    assert refresh_data["refresh_token"] != refresh_token


@pytest.mark.asyncio
async def test_refresh_token_not_found(
    client,
    db_session: AsyncSession,
):
    user = User(
        email="test@example.com",
        password_hash=hash_password("StrongPassword123"),
        is_active=True,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    refresh_token = create_refresh_token(
        data={
            "sub": str(user.id),
            "session_id": "not-found-session",
        },
        jti="test-jti",
    )

    response = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid session"


@pytest.mark.asyncio
async def test_refresh_without_user_id(client):
    refresh_token = create_refresh_token(
        data={
            "session_id": "missing-user-id-session",
        },
        jti="test-jti",
    )

    response = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid refresh token"


@pytest.mark.asyncio
async def test_refresh_without_session_id(client):
    refresh_token = create_refresh_token(
        data={
            "user_id": "1",
        },
        jti="test-jti",
    )

    response = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid refresh token"


@pytest.mark.asyncio
async def test_refresh_token_reuse_after_rotation(client):
    user_data = {
        "email": "api-refresh-rotation@example.com",
        "password": "StrongPassword123",
    }

    register_response = await client.post(
        "/auth/register",
        json=user_data,
    )

    login_response = await client.post(
        "/auth/login",
        json=user_data,
    )

    login_data = login_response.json()
    old_refresh_token = login_data["refresh_token"]

    refresh_response = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": old_refresh_token,
        },
    )

    assert register_response.status_code == 200
    assert login_response.status_code == 200
    assert refresh_response.status_code == 200

    refresh_data = refresh_response.json()
    new_refresh_token = refresh_data["refresh_token"]

    assert new_refresh_token
    assert new_refresh_token != old_refresh_token

    reuse_response = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": old_refresh_token,
        },
    )

    assert reuse_response.status_code == 401
    assert reuse_response.json()["detail"] == "Invalid token"


@pytest.mark.asyncio
async def test_me_invalid_access_token(client):
    response = await client.get(
        "/auth/me",
        headers={
            "Authorization": "Bearer invalid-access-token",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_access_token_without_user_id(client):
    access_token = create_access_token(
        data={
            "session_id": "missing-user-id-session",
        }
    )

    response = await client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_me_expired_access_token(client):
    access_token = create_access_token(
        data={
            "sub": "1",
            "session_id": "expired-session",
        },
        expires_delta=timedelta(seconds=-1),
    )

    response = await client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_access_token(client):
    access_token = create_access_token(
        data={
            "sub": "1",
            "session_id": "wrong-token-type-session",
        }
    )

    response = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": access_token,
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid refresh token"


@pytest.mark.asyncio
async def test_inactive_user_cannot_access_with_old_token(
    client,
    db_session,
):
    user = User(
        email="active@example.com",
        password_hash=hash_password("password123"),
        is_active=True,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    login_response = await client.post(
        "/auth/login",
        json={
            "email": "active@example.com",
            "password": "password123",
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    user.is_active = False
    await db_session.commit()

    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_concurrent_refresh_with_same_token_only_one_succeeds(client):
    user_data = {
        "email": "concurrent-refresh@example.com",
        "password": "StrongPassword123",
    }

    register_response = await client.post(
        "/auth/register",
        json=user_data,
    )

    assert register_response.status_code == 200

    login_response = await client.post(
        "/auth/login",
        json=user_data,
    )

    assert login_response.status_code == 200

    refresh_token = login_response.json()["refresh_token"]

    start_event = asyncio.Event()

    async def refresh():
        await start_event.wait()

        return await client.post(
            "/auth/refresh",
            json={
                "refresh_token": refresh_token,
            },
        )

    tasks = [asyncio.create_task(refresh()) for _ in range(10)]

    start_event.set()

    responses = await asyncio.gather(*tasks)

    statuses = [response.status_code for response in responses]

    assert statuses.count(200) == 1
    assert statuses.count(401) == 9


@pytest.mark.asyncio
async def test_logout_success(client):
    user_data = {
        "email": "api-logout-success@example.com",
        "password": "StrongPassword123",
    }

    register_response = await client.post(
        "/auth/register",
        json=user_data,
    )

    login_response = await client.post(
        "/auth/login",
        json=user_data,
    )

    login_data = login_response.json()
    access_token = login_data["access_token"]
    logout_response = await client.post(
        "/auth/logout",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )
    assert register_response.status_code == 200
    assert login_response.status_code == 200
    assert logout_response.status_code == 200


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client):
    user_data = {
        "email": "api-logout-revoke@example.com",
        "password": "StrongPassword123",
    }

    register_response = await client.post(
        "/auth/register",
        json=user_data,
    )

    login_response = await client.post(
        "/auth/login",
        json=user_data,
    )

    login_data = login_response.json()
    access_token = login_data["access_token"]
    refresh_token = login_data["refresh_token"]

    logout_response = await client.post(
        "/auth/logout",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )
    refresh_response = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )
    assert register_response.status_code == 200
    assert login_response.status_code == 200
    assert logout_response.status_code == 200
    assert refresh_response.status_code == 401
    assert refresh_response.json()["detail"] == "Invalid session"


@pytest.mark.asyncio
async def test_revoke_session_revokes_access_token(client):
    user_data = {
        "email": "api-session-revoke-access@example.com",
        "password": "StrongPassword123",
    }

    register_response = await client.post(
        "/auth/register",
        json=user_data,
    )

    login_response = await client.post(
        "/auth/login",
        json=user_data,
    )

    login_data = login_response.json()
    access_token = login_data["access_token"]

    sessions_response = await client.get(
        "/sessions/",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    session_id = sessions_response.json()[0]["session_id"]

    revoke_response = await client.delete(
        f"/sessions/{session_id}",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    me_response = await client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert register_response.status_code == 200
    assert login_response.status_code == 200
    assert sessions_response.status_code == 200
    assert revoke_response.status_code == 204
    assert me_response.status_code == 401


@pytest.mark.asyncio
async def test_logout_without_access_token(client):
    response = await client.post(
        "/auth/logout",
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_all_revokes_all_sessions(client):
    user_data = {
        "email": "api-logout-all@example.com",
        "password": "StrongPassword123",
    }

    register_response = await client.post(
        "/auth/register",
        json=user_data,
    )

    login_response_1 = await client.post(
        "/auth/login",
        json=user_data,
    )

    login_response_2 = await client.post(
        "/auth/login",
        json=user_data,
    )
    login_data_1 = login_response_1.json()
    login_data_2 = login_response_2.json()

    access_token_1 = login_data_1["access_token"]
    refresh_token_1 = login_data_1["refresh_token"]

    refresh_token_2 = login_data_2["refresh_token"]
    logout_all_response = await client.post(
        "/auth/logout-all",
        headers={
            "Authorization": f"Bearer {access_token_1}",
        },
    )
    refresh_response_1 = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": refresh_token_1,
        },
    )

    refresh_response_2 = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": refresh_token_2,
        },
    )
    assert register_response.status_code == 200
    assert login_response_1.status_code == 200
    assert login_response_2.status_code == 200

    assert logout_all_response.status_code == 200

    assert refresh_response_1.status_code == 401
    assert refresh_response_2.status_code == 401

    assert refresh_response_1.json()["detail"] == "Invalid session"
    assert refresh_response_2.json()["detail"] == "Invalid session"


@pytest.mark.asyncio
async def test_logout_revokes_access_token(client):
    user_data = {
        "email": "api-logout-access@example.com",
        "password": "StrongPassword123",
    }

    register_response = await client.post(
        "/auth/register",
        json=user_data,
    )

    login_response = await client.post(
        "/auth/login",
        json=user_data,
    )

    login_data = login_response.json()
    access_token = login_data["access_token"]

    logout_response = await client.post(
        "/auth/logout",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )
    me_response = await client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert register_response.status_code == 200
    assert login_response.status_code == 200
    assert logout_response.status_code == 200
    assert me_response.status_code == 401


@pytest.mark.asyncio
async def test_logout_all_without_access_token(client):
    response = await client.post(
        "/auth/logout-all",
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_without_access_token(client):
    response = await client.get(
        "/auth/me",
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_inactive_user_cannot_refresh(
    client,
    db_session,
):
    user = User(
        email="inactive-refresh@example.com",
        password_hash=hash_password("password123"),
        is_active=True,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    login_response = await client.post(
        "/auth/login",
        json={
            "email": "inactive-refresh@example.com",
            "password": "password123",
        },
    )

    assert login_response.status_code == 200

    refresh_token = login_response.json()["refresh_token"]

    user.is_active = False
    await db_session.commit()

    response = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid refresh token"


@pytest.mark.asyncio
async def test_me_access_token_with_invalid_jti(client):
    access_token = jwt.encode(
        {
            "sub": "1",
            "session_id": "invalid-jti-session",
            "jti": 12345,
            "exp": datetime.now(UTC) + timedelta(minutes=5),
            "type": "access",
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = await client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_access_token_with_invalid_session_id(client):
    access_token = jwt.encode(
        {
            "sub": "1",
            "session_id": 12345,
            "jti": "valid-jti",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
            "type": "access",
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = await client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_with_invalid_jti(client):
    refresh_token = jwt.encode(
        {
            "sub": "1",
            "session_id": "invalid-jti-session",
            "jti": 12345,
            "exp": datetime.now(UTC) + timedelta(days=1),
            "type": "refresh",
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_with_invalid_session_id(client):
    refresh_token = jwt.encode(
        {
            "sub": "1",
            "session_id": 12345,
            "jti": "valid-jti",
            "exp": datetime.now(UTC) + timedelta(days=1),
            "type": "refresh",
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    response = await client.post(
        "/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_concurrent_refresh_does_not_revoke_session(client):
    user_data = {
        "email": "concurrent-refresh-session@example.com",
        "password": "StrongPassword123",
    }

    register_response = await client.post(
        "/auth/register",
        json=user_data,
    )

    assert register_response.status_code == 200

    login_response = await client.post(
        "/auth/login",
        json=user_data,
    )

    assert login_response.status_code == 200

    refresh_token = login_response.json()["refresh_token"]

    start_event = asyncio.Event()

    async def refresh():
        await start_event.wait()

        return await client.post(
            "/auth/refresh",
            json={
                "refresh_token": refresh_token,
            },
        )

    tasks = [asyncio.create_task(refresh()) for _ in range(10)]

    start_event.set()

    responses = await asyncio.gather(*tasks)

    statuses = [response.status_code for response in responses]

    assert statuses.count(200) == 1
    assert statuses.count(401) == 9

    successful_response = next(
        response for response in responses if response.status_code == 200
    )

    access_token = successful_response.json()["access_token"]

    me_response = await client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert me_response.status_code == 200
