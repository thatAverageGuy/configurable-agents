"""
Tests for T-015: Memory extraction opt-in (extract_facts field).

Covers:
- extract_facts=False (default) skips _extract_memory_facts entirely
- extract_facts=True triggers fact extraction
- extraction_model overrides the LLM used for extraction
- _build_extraction_llm provider inference
- MemoryConfig schema validation (new fields, backward compatibility)
"""

from unittest.mock import MagicMock, call, patch

import pytest
from pydantic import BaseModel

from configurable_agents.config.schema import LLMConfig, MemoryConfig
from configurable_agents.core.node_executor import _build_extraction_llm


# ─────────────────────────────────────────────
# MemoryConfig schema tests
# ─────────────────────────────────────────────

class TestMemoryConfigSchema:
    def test_extract_facts_defaults_false(self):
        cfg = MemoryConfig()
        assert cfg.extract_facts is False

    def test_extraction_model_defaults_none(self):
        cfg = MemoryConfig()
        assert cfg.extraction_model is None

    def test_extract_facts_can_be_enabled(self):
        cfg = MemoryConfig(extract_facts=True)
        assert cfg.extract_facts is True

    def test_extraction_model_accepts_string(self):
        cfg = MemoryConfig(extract_facts=True, extraction_model="gpt-4o-mini")
        assert cfg.extraction_model == "gpt-4o-mini"

    def test_existing_fields_unchanged(self):
        """Backward compat: existing MemoryConfig fields still work."""
        cfg = MemoryConfig(enabled=True, default_scope="workflow", max_entries=20)
        assert cfg.enabled is True
        assert cfg.default_scope == "workflow"
        assert cfg.max_entries == 20


# ─────────────────────────────────────────────
# _build_extraction_llm tests
# ─────────────────────────────────────────────

class TestBuildExtractionLlm:
    def _base_config(self):
        return LLMConfig(provider="openai", model="gpt-4o", temperature=0.7)

    def test_infers_openai_from_gpt_prefix(self):
        base = self._base_config()
        with patch("configurable_agents.core.node_executor.create_llm") as mock_create:
            _build_extraction_llm("gpt-4o-mini", base)
            created_config = mock_create.call_args[0][0]
            assert created_config.model == "gpt-4o-mini"
            assert created_config.provider == "openai"

    def test_infers_anthropic_from_claude_prefix(self):
        base = self._base_config()
        with patch("configurable_agents.core.node_executor.create_llm") as mock_create:
            _build_extraction_llm("claude-haiku-4-5", base)
            created_config = mock_create.call_args[0][0]
            assert created_config.model == "claude-haiku-4-5"
            assert created_config.provider == "anthropic"

    def test_infers_google_from_gemini_prefix(self):
        base = self._base_config()
        with patch("configurable_agents.core.node_executor.create_llm") as mock_create:
            _build_extraction_llm("gemini-flash-1.5", base)
            created_config = mock_create.call_args[0][0]
            assert created_config.model == "gemini-flash-1.5"
            assert created_config.provider == "google"

    def test_unknown_prefix_keeps_base_provider(self):
        base = self._base_config()
        with patch("configurable_agents.core.node_executor.create_llm") as mock_create:
            _build_extraction_llm("some-unknown-model", base)
            created_config = mock_create.call_args[0][0]
            assert created_config.model == "some-unknown-model"
            assert created_config.provider == "openai"  # inherited from base

    def test_base_config_temperature_preserved(self):
        base = self._base_config()
        with patch("configurable_agents.core.node_executor.create_llm") as mock_create:
            _build_extraction_llm("gpt-4o-mini", base)
            created_config = mock_create.call_args[0][0]
            assert created_config.temperature == 0.7


# ─────────────────────────────────────────────
# execute_node integration: extract_facts guard
# ─────────────────────────────────────────────

class _SimpleState(BaseModel):
    result: str = ""


def _make_node_config(extract_facts=False, extraction_model=None):
    from configurable_agents.config.schema import NodeConfig, OutputSchema, OutputSchemaField
    return NodeConfig(
        id="test_node",
        prompt="Say hi",
        output_schema=OutputSchema(
            type="object",
            fields=[OutputSchemaField(name="result", type="str")]
        ),
        outputs=["result"],
        memory=MemoryConfig(
            enabled=True,
            extract_facts=extract_facts,
            extraction_model=extraction_model,
        ),
    )


def _make_mock_llm_result():
    from configurable_agents.llm import LLMUsageMetadata
    mock_llm = MagicMock()
    mock_result = MagicMock()
    mock_result.result = "hello"
    mock_usage = LLMUsageMetadata(input_tokens=10, output_tokens=5)
    return mock_llm, mock_result, mock_usage


class TestExecuteNodeExtractionGuard:
    """Test that the extract_facts flag controls whether _extract_memory_facts is called."""

    def _run_with_memory(self, extract_facts, extraction_model=None):
        from configurable_agents.core import execute_node

        node_config = _make_node_config(
            extract_facts=extract_facts,
            extraction_model=extraction_model,
        )
        mock_llm, mock_result, mock_usage = _make_mock_llm_result()

        mock_memory_repo = MagicMock()
        mock_memory_repo.list.return_value = []

        mock_tracker = MagicMock()
        mock_tracker.memory_repo = mock_memory_repo

        with patch("configurable_agents.core.node_executor.create_llm", return_value=mock_llm), \
             patch("configurable_agents.core.node_executor.call_llm_structured",
                   return_value=(mock_result, mock_usage)), \
             patch("configurable_agents.core.node_executor.AgentMemory") as MockAgentMemory, \
             patch("configurable_agents.core.node_executor._extract_memory_facts",
                   return_value=[]) as mock_extract, \
             patch("configurable_agents.core.node_executor.CostEstimator"):

            mock_agent_mem = MagicMock()
            MockAgentMemory.return_value = mock_agent_mem
            mock_agent_mem.list.return_value = []

            execute_node(
                node_config=node_config,
                state=_SimpleState(result=""),
                tracker=mock_tracker,
            )

            return mock_extract

    def test_extract_facts_false_skips_extraction(self):
        mock_extract = self._run_with_memory(extract_facts=False)
        mock_extract.assert_not_called()

    def test_extract_facts_true_calls_extraction(self):
        mock_extract = self._run_with_memory(extract_facts=True)
        mock_extract.assert_called_once()

    def test_extraction_model_creates_different_llm(self):
        from configurable_agents.core import execute_node

        node_config = _make_node_config(
            extract_facts=True,
            extraction_model="gpt-4o-mini",
        )
        mock_llm, mock_result, mock_usage = _make_mock_llm_result()

        with patch("configurable_agents.core.node_executor.create_llm",
                   return_value=mock_llm) as mock_create_llm, \
             patch("configurable_agents.core.node_executor.call_llm_structured",
                   return_value=(mock_result, mock_usage)), \
             patch("configurable_agents.core.node_executor.AgentMemory") as MockAgentMemory, \
             patch("configurable_agents.core.node_executor._extract_memory_facts",
                   return_value=[]), \
             patch("configurable_agents.core.node_executor.CostEstimator"):

            mock_agent_mem = MagicMock()
            MockAgentMemory.return_value = mock_agent_mem
            mock_agent_mem.list.return_value = []

            mock_tracker2 = MagicMock()
            mock_tracker2.memory_repo = MagicMock()
            mock_tracker2.memory_repo.list.return_value = []

            execute_node(
                node_config=node_config,
                state=_SimpleState(result=""),
                tracker=mock_tracker2,
            )

            # create_llm is called twice: once for node LLM, once for extraction LLM
            assert mock_create_llm.call_count == 2
            # Second call should have gpt-4o-mini as the model
            extraction_config = mock_create_llm.call_args_list[1][0][0]
            assert extraction_config.model == "gpt-4o-mini"
