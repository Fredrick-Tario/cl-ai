import pytest

from cl_ai.security import SecretDetector


@pytest.mark.parametrize(
    "command",
    [
        "curl -H 'Authorization: Bearer abcdefghijklmnopqrstuvwxyz' https://example.test",
        "tool --api-key literal-secret-value",
        "PASSWORD=hunter2 deploy",
        "curl https://user:password@example.test/path",
        "echo sk-exampleCredentialValue123",
        "cat '-----BEGIN PRIVATE KEY-----'",
    ],
)
def test_detects_obvious_literal_secrets(command: str) -> None:
    assert SecretDetector().scan(command)


@pytest.mark.parametrize(
    "command",
    [
        "tool --api-key $QWEN_API_KEY",
        "tool --password '${DB_PASSWORD}'",
        "export API_KEY=<your-api-key>",
        "kubectl create secret generic app-config",
        "terraform plan -var-file=secrets.tfvars",
    ],
)
def test_allows_references_placeholders_and_noncredential_secret_words(
    command: str,
) -> None:
    assert SecretDetector().scan(command) == []

