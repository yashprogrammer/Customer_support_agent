"""Compatibility tests for root module wrappers."""

from __future__ import annotations


def test_wrapper_imports_resolve():
    import config
    import copilot
    import database
    import memory
    import models
    import rag
    import tools

    assert hasattr(config, "Settings")
    assert hasattr(config, "get_settings")

    assert hasattr(models, "TicketCreateRequest")
    assert hasattr(models, "DraftResponse")

    assert hasattr(rag, "KnowledgeBaseService")
    assert hasattr(memory, "CustomerMemoryStore")
    assert hasattr(tools, "get_support_tools")

    assert hasattr(database, "init_db")
    assert hasattr(database, "create_ticket")

    assert hasattr(copilot, "SupportCopilot")


def test_main_wrapper_exposes_app():
    import main

    assert hasattr(main, "app")
