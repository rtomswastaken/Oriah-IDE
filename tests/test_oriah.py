"""Unit and headless UI tests for Oriah IDE."""

import unittest
from pathlib import Path
from oriah.state import AppState, AgentConfig, EditorTab
from oriah.app import OriahIDE
from oriah.widgets.agent_panel import AgentModePanel
from oriah.widgets.checklist_panel import ChecklistPanel
from oriah.widgets.directory_panel import DirectoryPanel
from oriah.widgets.editor_panel import EditorPanel
from oriah.widgets.terminal_panel import TerminalPanel


class TestOriahState(unittest.TestCase):
    def setUp(self):
        self.state = AppState(root_dir=".")

    def test_default_agents(self):
        self.assertGreaterEqual(len(self.state.agents), 3)
        names = [a.name for a in self.state.agents]
        self.assertIn("Gemma 2 Coder", names)
        self.assertIn("Qwen Architect", names)

    def test_add_agent(self):
        initial_count = len(self.state.agents)
        new_agent = self.state.add_agent(
            name="Claude Specialist",
            model="claude-3-5-sonnet",
            provider="Anthropic",
            role="Refactoring Guru",
        )
        self.assertEqual(len(self.state.agents), initial_count + 1)
        self.assertEqual(self.state.active_agent_id, new_agent.id)
        self.assertEqual(self.state.get_active_agent().name, "Claude Specialist")

    def test_checklist_progress(self):
        initial_progress = self.state.get_checklist_progress()
        self.assertGreater(initial_progress, 0)
        # Toggle first item
        item = self.state.checklist[0]
        was_done = item.done
        self.state.toggle_checklist(item.id)
        self.assertEqual(item.done, not was_done)

    def test_open_file(self):
        test_file = Path("test_file.py")
        test_file.write_text("print('hello world')", encoding="utf-8")
        try:
            tab = self.state.open_file(test_file)
            self.assertEqual(tab.filename, "test_file.py")
            self.assertEqual(tab.language, "python")
            self.assertIn("hello world", tab.content)
            self.assertEqual(self.state.get_active_tab(), tab)
        finally:
            if test_file.exists():
                test_file.unlink()


class TestOriahHeadlessApp(unittest.IsolatedAsyncioTestCase):
    async def test_app_composition_and_mode_toggle(self):
        app = OriahIDE(root_dir=".")
        async with app.run_test() as pilot:
            # Check all 4 quadrants mounted
            self.assertIsNotNone(app.query_one(DirectoryPanel))
            self.assertIsNotNone(app.query_one(ChecklistPanel))
            self.assertIsNotNone(app.query_one(EditorPanel))
            self.assertIsNotNone(app.query_one(AgentModePanel))
            self.assertIsNotNone(app.query_one(TerminalPanel))

            # Initial mode should be agent
            agent_panel = app.query_one("#agent-mode-panel", AgentModePanel)
            terminal_panel = app.query_one("#terminal-panel", TerminalPanel)
            self.assertTrue(agent_panel.display)
            self.assertFalse(terminal_panel.display)

            # Toggle to terminal mode via action
            app.action_toggle_bottom_mode()
            await pilot.pause()
            self.assertFalse(agent_panel.display)
            self.assertTrue(terminal_panel.display)

            # Test terminal command execution
            terminal_panel.run_command("echo 'testing terminal runner'")
            await pilot.pause(0.2)
            self.assertIn("echo 'testing terminal runner'", app.state.terminal_history)

            # Toggle back to agent mode
            app.action_toggle_bottom_mode()
            await pilot.pause()
            self.assertTrue(agent_panel.display)
            self.assertFalse(terminal_panel.display)

            # Test prompt submission in Agent Mode
            prompt_input = agent_panel.query_one("#agent-prompt-input")
            prompt_input.value = "Write a binary search in Rust"
            agent_panel._submit_prompt()
            await pilot.pause(0.2)
            self.assertTrue(any("Write a binary search in Rust" in line for line in app.state.agent_logs))

            # Test saving editor file via action
            app.action_save_file()
            await pilot.pause()

            # Test adding an agent programmatically
            new_agent = app.state.add_agent(
                name="Gemma Code Reviewer",
                model="gemma2:9b",
                provider="Ollama (Local)",
                role="Code Auditor",
            )
            agent_panel.refresh_cards()
            await pilot.pause()
            self.assertIn(new_agent, app.state.agents)
            self.assertEqual(app.state.active_agent_id, new_agent.id)


if __name__ == "__main__":
    unittest.main()
