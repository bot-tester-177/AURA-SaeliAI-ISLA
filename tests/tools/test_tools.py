from __future__ import annotations

from unittest import TestCase

from ISLA.tools.tool_router import ToolCall, ToolRouter


class ToolRouterTests(TestCase):
    def test_registers_and_executes_callable_tools(self) -> None:
        router = ToolRouter()
        router.register("echo", lambda text="": text)

        self.assertEqual(router.execute(ToolCall(name="echo", arguments={"text": "ok"})), "ok")

    def test_executes_objects_with_execute_method(self) -> None:
        class Handler:
            def execute(self, arguments: dict[str, object]) -> str:
                return str(arguments["value"])

        router = ToolRouter()
        router.register("handler", Handler())

        self.assertEqual(router.execute(ToolCall(name="handler", arguments={"value": 42})), "42")

    def test_rejects_invalid_tools_and_unknown_calls(self) -> None:
        router = ToolRouter()

        with self.assertRaises(ValueError):
            router.register("   ", lambda: None)

        with self.assertRaises(KeyError):
            router.execute(ToolCall(name="missing", arguments={}))