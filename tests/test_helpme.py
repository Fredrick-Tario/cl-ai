import json

import pytest

from cl_ai.ai.provider import AIProvider, ProviderError
from cl_ai.helpme import OnlineHelpError, OnlineHelpService, WebDocument, WebRetriever


class FakeRetriever:
    def __init__(self):
        self.calls = 0

    def retrieve(self, question):
        self.calls += 1
        assert question
        return [
            WebDocument(
                title="Terraform import command reference",
                url="https://developer.hashicorp.com/terraform/cli/commands/import",
                text="The terraform import command imports existing resources into state.",
            )
        ]


class FakeProvider(AIProvider):
    def __init__(self, response):
        self.response = response
        self.calls = 0

    def chat(self, messages):
        self.calls += 1
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def response_json(**overrides):
    data = {
        "explanation": "Import associates an existing object with a Terraform address.",
        "prerequisites": ["Define the resource in configuration first."],
        "commands": [
            {
                "command": "terraform import ADDRESS ID",
                "explanation": "Import the remote object into Terraform state.",
                "provenance": "documented_example",
                "source_indices": [1],
                "risk_level": "medium",
                "risk_notes": ["Back up state before changing it."],
            }
        ],
        "warnings": ["This changes Terraform state, not the remote object."],
    }
    data.update(overrides)
    return json.dumps(data)


def test_online_help_uses_retrieved_sources_and_validates_commands() -> None:
    service = OnlineHelpService(FakeProvider(response_json()), FakeRetriever())

    result = service.research("What does terraform import do?")

    assert result.commands[0].command == "terraform import ADDRESS ID"
    assert result.commands[0].source_indices == [1]
    assert result.documents[0].url.startswith("https://developer.hashicorp.com/")


def test_online_help_normalizes_single_string_list_fields() -> None:
    data = json.loads(response_json())
    data["prerequisites"] = "Docker Compose is installed."
    data["warnings"] = "The command does not start containers."
    data["commands"][0]["risk_notes"] = "Read-only status command."

    result = OnlineHelpService(
        FakeProvider(json.dumps(data)),
        FakeRetriever(),
    ).research("docker compose ps")

    assert result.prerequisites == ["Docker Compose is installed."]
    assert result.warnings == ["The command does not start containers."]
    assert result.commands[0].risk_notes == ["Read-only status command."]


def test_online_help_rejects_fabricated_source_index() -> None:
    command = json.loads(response_json())["commands"][0]
    command["source_indices"] = [99]
    provider = FakeProvider(response_json(commands=[command]))

    with pytest.raises(OnlineHelpError, match="malformed"):
        OnlineHelpService(provider, FakeRetriever()).research("terraform import")

    assert provider.calls == 2


def test_online_help_propagates_safe_provider_failure() -> None:
    provider = FakeProvider(ProviderError("AI provider request failed safely"))

    with pytest.raises(ProviderError, match="failed safely"):
        OnlineHelpService(provider, FakeRetriever()).research("terraform import")


class FakeHeaders(dict):
    def get_content_charset(self):
        return "utf-8"


class FakeResponse:
    def __init__(self, body: str) -> None:
        self.body = body.encode()
        self.headers = FakeHeaders({"Content-Type": "text/html; charset=utf-8"})

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        return self.body[:size]


class FakeOpener:
    def __init__(self) -> None:
        self.urls = []

    def open(self, request, timeout):
        assert timeout == 5
        self.urls.append(request.full_url)
        if len(self.urls) == 1:
            return FakeResponse(
                '<a class="result__a" href="https://untrusted.example/docs">Bad</a>'
                '<a class="result__a" '
                'href="https://developer.hashicorp.com/terraform/cli/commands/import">'
                'Terraform import</a>'
            )
        return FakeResponse(
            "<html><title>Terraform import</title><main><h1>Import</h1>"
            "<p>The terraform import command associates an existing remote resource "
            "with a resource address in Terraform state. Define the resource first." 
            "</p></main></html>"
        )


def test_web_retriever_searches_online_and_fetches_only_official_sources() -> None:
    opener = FakeOpener()

    documents = WebRetriever(timeout=5, opener=opener).retrieve("terraform import")

    assert len(opener.urls) == 2
    assert "duckduckgo.com" in opener.urls[0]
    assert opener.urls[1].startswith("https://developer.hashicorp.com/")
    assert documents[0].url == opener.urls[1]


def test_web_retriever_rejects_invalid_question_before_network() -> None:
    opener = FakeOpener()

    with pytest.raises(OnlineHelpError, match="must not be blank"):
        WebRetriever(opener=opener).retrieve("   ")

    assert opener.urls == []


def test_bing_redirect_is_decoded_before_official_host_check() -> None:
    encoded = "a1aHR0cHM6Ly9kb2NzLmRvY2tlci5jb20vcmVmZXJlbmNlL2NsaS9kb2NrZXIvY29udGFpbmVyL2xvZ3Mv"
    url = f"https://www.bing.com/ck/a?u={encoded}&ntb=1"

    decoded = WebRetriever._result_url(url)

    assert decoded == "https://docs.docker.com/reference/cli/docker/container/logs/"


def test_online_help_rejects_literal_secret_suggestion() -> None:
    command = json.loads(response_json())["commands"][0]
    command["command"] = "deploy --token literal-sensitive-value"
    provider = FakeProvider(response_json(commands=[command]))

    with pytest.raises(OnlineHelpError, match="malformed"):
        OnlineHelpService(provider, FakeRetriever()).research("deploy")


def test_online_help_blocks_question_secret_before_network_or_model() -> None:
    retriever = FakeRetriever()
    provider = FakeProvider(response_json())

    with pytest.raises(OnlineHelpError, match="sensitive data") as error:
        OnlineHelpService(provider, retriever).research(
            "Explain deploy --token literal-sensitive-value"
        )

    assert "literal-sensitive-value" not in str(error.value)
    assert retriever.calls == 0
    assert provider.calls == 0


def test_official_page_redirect_to_untrusted_host_is_rejected() -> None:
    class RedirectedResponse(FakeResponse):
        def geturl(self):
            return "https://untrusted.example/injected"

    class RedirectingOpener:
        def open(self, request, timeout):
            return RedirectedResponse("<html><p>untrusted content</p></html>")

    retriever = WebRetriever(opener=RedirectingOpener())

    with pytest.raises(OnlineHelpError, match="untrusted host"):
        retriever._read(
            retriever._request("https://docs.docker.com/reference/"),
            "Documentation page retrieval failed",
        )
