"""Tool routing for Isla."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ToolCall:
    name: str
    arguments: dict[str, object]


@dataclass(slots=True)
class ToolRouter:
    """Dispatches safe, explicit tool calls."""

    registry: dict[str, object] = field(default_factory=dict)

    def register(self, name: str, handler: object) -> None:
        if not name.strip():
            raise ValueError("Tool name cannot be empty.")
        if not callable(handler) and not hasattr(handler, "execute"):
            raise TypeError("Tool handlers must be callable or expose an execute method.")
        self.registry[name] = handler

    def execute(self, call: ToolCall) -> object:
        handler = self.registry.get(call.name)
        if handler is None:
            raise KeyError(f"No tool registered for {call.name!r}.")

        if hasattr(handler, "execute"):
            return handler.execute(call.arguments)

        if callable(handler):
            try:
                return handler(**call.arguments)
            except TypeError:
                return handler(call.arguments)

        raise TypeError(f"Tool {call.name!r} is not executable.")