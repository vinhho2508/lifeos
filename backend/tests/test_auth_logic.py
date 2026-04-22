import pytest
from src.core.database import settings

def test_is_authorized_user():
    # Helper to check if email is authorized
    from src.core.auth import is_authorized_user
    
    assert is_authorized_user(settings.ALLOWED_USER_EMAIL) is True
    assert is_authorized_user("wrong@gmail.com") is False
    assert is_authorized_user("") is False
