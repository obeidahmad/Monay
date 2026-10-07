"""Monay's HTTP API — the web front end's way into the budgeting engine.

A delivery layer beside ``tui/`` (docs/DEVELOPING.md): it turns requests into
calls on ``app.budgeting.BudgetingService`` and the resulting ``Month`` into
JSON. No budgeting rule lives here.

Run it with ``python -m monay.api`` (see ``settings.py`` for the environment
variables), or under a reloader with
``uvicorn monay.api.app:create_app --factory --reload``.
"""
