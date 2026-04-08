# api/tests/crud/test_users.py
from crud.users import create_user, get_user_by_mail, get_user_by_id, authenticate_user, update_user_password
from models.users import Users
from sqlalchemy.orm import Session
import pytest


def test_create_user(db: Session):
    user = create_user(
        db,
        mail="newuser@example.com",
        username="newuser",
        password="MySecretPassword123",
        role="user"
    )
    assert user.idusers is not None
    assert user.mail == "newuser@example.com"
    assert user.username == "newuser"
    assert user.role == "user"
    # Ensure password is not plain text
    assert user.password_hash != "MySecretPassword123"


def test_get_user_by_mail(db: Session):
    create_user(db, mail="t2@example.com", username="t2",
                password="P1", role="user")
    user = get_user_by_mail(db, mail="t2@example.com")
    assert user is not None
    assert user.mail == "t2@example.com"

    non_existent = get_user_by_mail(db, mail="doesnotexist@example.com")
    assert non_existent is None


def test_get_user_by_id(db: Session):
    user_created = create_user(
        db, mail="t3@example.com", username="t3", password="P1", role="user")
    user = get_user_by_id(db, user_id=user_created.idusers)
    assert user is not None
    assert user.idusers == user_created.idusers


def test_authenticate_user(db: Session):
    create_user(db, mail="auth@example.com", username="auth",
                password="MySecretPassword123", role="user")
    user = authenticate_user(db, mail="auth@example.com",
                             password="MySecretPassword123")
    assert user is not None
    assert user.mail == "auth@example.com"

    # Wrong password
    wrong_pass = authenticate_user(
        db, mail="auth@example.com", password="WrongPassword")
    assert wrong_pass is None

    # Wrong email
    wrong_email = authenticate_user(
        db, mail="doesnotexist@example.com", password="MySecretPassword123")
    assert wrong_email is None


def test_update_user_password(db: Session):
    user = create_user(db, mail="update@example.com",
                       username="update", password="OldPassword", role="user")
    old_hash = user.password_hash

    updated_user = update_user_password(
        db, user=user, new_password="NewPassword123")
    assert updated_user.password_hash != old_hash

    # Try authenticating with new password
    auth_user = authenticate_user(
        db, mail="update@example.com", password="NewPassword123")
    assert auth_user is not None
