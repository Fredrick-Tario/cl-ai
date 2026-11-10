import json

import pytest

from cl_ai.ai.provider import AIProvider
from cl_ai.vault.documenter import CommandDocumenter, DocumentationGenerationError


def documentation_json(**overrides) -> str:
    data = {
        "title": "Preview Terraform changes",
        "category": "Terraform",
        "subcategory": "Planning",
        "description": "Shows proposed infrastructure changes without applying them.",
        "flag_breakdown": [
            {"token": "plan", "explanation": "Build a proposed change plan."}
        ],
        "tags": ["terraform", "plan"],
        "risk_level": "low",
        "risk_notes": ["Review the plan before applying changes."],
    }
    data.update(overrides)
    return json.dumps(data)


class SequencedProvider(AIProvider):
    def __init__(self, responses: list[str]) -> None:
        self.responses = iter(responses)
        self.calls = 0
        self.last_messages = []

    def chat(self, messages):
        self.calls += 1
        self.last_messages = list(messages)
        return next(self.responses)


def test_documenter_parses_valid_structured_response() -> None:
    provider = SequencedProvider([documentation_json()])

    result = CommandDocumenter(provider).generate("terraform plan")

    assert result.title == "Preview Terraform changes"
    assert result.category == "Terraform"
    assert result.flag_breakdown[0].token == "plan"
    assert provider.calls == 1


def test_documenter_retries_one_malformed_response() -> None:
    provider = SequencedProvider(["not json", documentation_json()])

    result = CommandDocumenter(provider).generate("terraform plan")

    assert result.risk_level.value == "low"
    assert provider.calls == 2


def test_documenter_rejects_two_malformed_responses() -> None:
    provider = SequencedProvider(["not json", '{"title": "incomplete"}'])

    with pytest.raises(DocumentationGenerationError, match="nothing was saved"):
        CommandDocumenter(provider).generate("terraform plan")


def test_deterministic_risk_can_raise_ai_risk_level() -> None:
    provider = SequencedProvider(
        [documentation_json(risk_level="low", risk_notes=[])]
    )

    result = CommandDocumenter(provider).generate("terraform destroy")

    assert result.risk_level.value == "critical"
    assert "Deletes Terraform-managed infrastructure." in result.risk_notes


def test_documenter_requests_short_straightforward_output() -> None:
    provider = SequencedProvider([documentation_json()])

    CommandDocumenter(provider).generate("terraform plan")

    prompt = provider.last_messages[0].content
    assert "title: at most 8 words" in prompt
    assert "description: one short sentence" in prompt
    assert "Avoid filler" in prompt


def test_command_length_is_bounded_before_provider_call() -> None:
    provider = SequencedProvider([documentation_json()])

    with pytest.raises(DocumentationGenerationError, match="too long"):
        CommandDocumenter(provider).generate("x" * 4001)

    assert provider.calls == 0
