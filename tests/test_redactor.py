"""Tests for SecretRedactor."""
import pytest
from vcm_os.memory.redactor import SecretRedactor


def test_redacts_api_key():
    r = SecretRedactor()
    secret = "sk-" + "1234567890abcdef1234567890"
    text = f"api_key = {secret}"
    result = r.redact(text)
    assert secret not in result
    assert "[REDACTED]" in result


def test_redacts_password():
    r = SecretRedactor()
    text = "password = super_secret_123"
    result = r.redact(text)
    assert "super_secret_123" not in result
    assert "[REDACTED]" in result


def test_redacts_connection_string():
    r = SecretRedactor()
    text = "postgres://user:secret_pass@localhost:5432/db"
    result = r.redact(text)
    assert "secret_pass" not in result
    assert "[REDACTED]" in result
    assert "postgres://user:" in result
    assert "@localhost:5432/db" in result


def test_redacts_jwt():
    r = SecretRedactor()
    secret = "eyJ" + "hbGciOiJIUzI1NiIs.eyJzdWIiOiIxMjM0NTY3ODkwIiw.name"
    text = f"token = {secret}"
    result = r.redact(text)
    assert secret not in result
    assert "[REDACTED]" in result


def test_redacts_aws_key():
    r = SecretRedactor()
    text = "AKIA" + "IOSFODNN7EXAMPLE"
    assert r.redact(text) == "[REDACTED]"


def test_redacts_private_key():
    r = SecretRedactor()
    text = (
        "-----BEGIN RSA " + "PRIVATE KEY-----\n"
        "MIIEpAIBAAKCAQEA...\n"
        "-----END RSA " + "PRIVATE KEY-----"
    )
    result = r.redact(text)
    assert "PRIVATE KEY" not in result
    assert "[REDACTED]" in result


def test_redacts_github_token():
    r = SecretRedactor()
    text = "ghp_" + ("x" * 36)
    assert r.redact(text) == "[REDACTED]"


def test_redacts_env_var():
    r = SecretRedactor()
    text = "DATABASE_PASSWORD=mysecretvalue123"
    result = r.redact(text)
    assert "mysecretvalue123" not in result
    assert "[REDACTED]" in result


def test_redacts_stripe_key():
    r = SecretRedactor()
    text = "sk_live_" + ("x" * 24)
    assert r.redact(text) == "[REDACTED]"


def test_leaves_clean_text_untouched():
    r = SecretRedactor()
    text = "This is a normal log message with no secrets."
    assert r.redact(text) == text


def test_detects_secrets():
    r = SecretRedactor()
    assert r.has_secrets("api_key = secret123") is True
    assert r.has_secrets("normal text") is False


def test_gets_secret_types():
    r = SecretRedactor()
    api_key = "sk-" + "1234567890abcdef"
    types = r.get_secret_types(f"api_key = {api_key} password = super_secret_123")
    assert "api_key" in types
    assert "password" in types
