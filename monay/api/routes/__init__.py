"""The API's routes, one module per resource.

Every handler does the same three things: read the request into domain values
(``api/parsing.py``), call one ``BudgetingService`` use case, and present the
result (``api/presenters.py``).
"""

# The path every month-scoped route hangs off.
MONTH = "/profiles/{profile_id}/months/{key}"
