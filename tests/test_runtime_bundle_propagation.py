"""Structural guards for complete provider runtime propagation."""

import inspect

from cli import HermesCLI
from hermes_cli.runtime_provider import (
    RUNTIME_AGENT_KWARG_KEYS,
    project_runtime_agent_kwargs,
)
from run_agent import AIAgent


def test_runtime_projection_has_one_complete_key_set():
    runtime = project_runtime_agent_kwargs({})
    assert tuple(runtime) == RUNTIME_AGENT_KWARG_KEYS


def test_cli_derived_agents_expand_runtime_bundle_instead_of_selecting_fields():
    background = inspect.getsource(HermesCLI._handle_background_command)
    btw = inspect.getsource(HermesCLI._handle_btw_command)
    for source in (background, btw):
        assert '**turn_route["runtime"]' in source
        assert 'api_key=turn_route["runtime"].get' not in source
        assert 'base_url=turn_route["runtime"].get' not in source


def test_background_review_exports_parent_runtime_bundle():
    source = inspect.getsource(AIAgent._spawn_background_review)
    assert "**self.export_runtime_agent_kwargs()" in source
    assert "provider=self.provider" not in source
