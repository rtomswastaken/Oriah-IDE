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

    def test_agent_api_fields_and_dict(self):
        agent = AgentConfig(
            id="agent-custom",
            name="Custom OpenAI",
            model="gpt-4o",
            provider="OpenAI",
            role="Lead Coder",
            api_key="sk-test-secret",
            base_url="https://api.openai.com/v1",
            temperature=0.2,
            max_tokens=2048,
        )
        self.assertEqual(agent.api_key, "sk-test-secret")
        self.assertEqual(agent.base_url, "https://api.openai.com/v1")
        self.assertEqual(agent.temperature, 0.2)
        self.assertEqual(agent.max_tokens, 2048)

        data = agent.to_dict()
        self.assertEqual(data["api_key"], "sk-test-secret")
        self.assertEqual(data["base_url"], "https://api.openai.com/v1")

        restored = AgentConfig.from_dict(data)
        self.assertEqual(restored.name, "Custom OpenAI")
        self.assertEqual(restored.api_key, "sk-test-secret")
        self.assertEqual(restored.base_url, "https://api.openai.com/v1")

    def test_agent_persistence_and_crud(self):
        import tempfile
        import shutil

        temp_dir = Path(tempfile.mkdtemp())
        try:
            state = AppState(root_dir=str(temp_dir))
            # Save defaults to disk
            state.save_agents_to_disk()
            config_file = temp_dir / ".oriah" / "agents.json"
            self.assertTrue(config_file.exists())

            # Add agent with API config
            agent = state.add_agent(
                name="DeepSeek Coder",
                model="deepseek-coder-v2",
                provider="Custom Endpoint",
                role="Senior Architect",
                api_key="sk-deepseek",
                base_url="https://api.deepseek.com/v1",
                temperature=0.3,
            )
            self.assertEqual(agent.api_key, "sk-deepseek")
            self.assertEqual(agent.base_url, "https://api.deepseek.com/v1")

            # Update agent
            updated = state.update_agent(
                agent_id=agent.id,
                name="DeepSeek Coder V2.5",
                model="deepseek-coder-v2.5",
                provider="Custom Endpoint",
                role="Staff Architect",
                api_key="sk-deepseek-new",
                base_url="https://api.deepseek.com/v1",
                instructions="Be extra strict with typing",
                temperature=0.1,
            )
            self.assertTrue(updated)
            self.assertEqual(agent.name, "DeepSeek Coder V2.5")
            self.assertEqual(agent.api_key, "sk-deepseek-new")
            self.assertEqual(agent.temperature, 0.1)

            # Reload from disk into new AppState instance
            new_state = AppState(root_dir=str(temp_dir))
            loaded_ids = [a.id for a in new_state.agents]
            self.assertIn(agent.id, loaded_ids)
            loaded_agent = next(a for a in new_state.agents if a.id == agent.id)
            self.assertEqual(loaded_agent.name, "DeepSeek Coder V2.5")
            self.assertEqual(loaded_agent.api_key, "sk-deepseek-new")

            # Delete agent
            deleted = new_state.delete_agent(agent.id)
            self.assertTrue(deleted)
            self.assertNotIn(agent.id, [a.id for a in new_state.agents])
            # Check fallback active agent
            self.assertTrue(bool(new_state.active_agent_id))

            # Check persistence of deletion
            reloaded_state = AppState(root_dir=str(temp_dir))
            self.assertNotIn(agent.id, [a.id for a in reloaded_state.agents])
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


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

    async def test_agent_manager_modal_interaction(self):
        import tempfile
        from oriah.widgets.agent_manager_modal import AgentManagerModal, AgentListItemButton
        from textual.widgets import Input, Button

        with tempfile.TemporaryDirectory() as temp_dir:
            app = OriahIDE(root_dir=temp_dir)
            async with app.run_test() as pilot:
                # Trigger manage agents modal action (Ctrl+M)
                app.action_manage_agents()
                await pilot.pause(0.3)

                # Modal should be screen on top
                self.assertIsInstance(app.screen, AgentManagerModal)
                modal = app.screen

                # Test switching active agent to agent-2 (Qwen Architect)
                second_agent_btn = next(
                    b for b in modal.query(AgentListItemButton) if b.agent_id == "agent-2"
                )
                second_agent_btn.press()
                await pilot.pause(0.2)

                set_active_btn = modal.query_one("#manager-btn-set-active", Button)
                set_active_btn.press()
                await pilot.pause(0.2)
                self.assertEqual(app.state.active_agent_id, "agent-2")

                # Switch to new agent form
                new_btn = modal.query_one("#manager-btn-new", Button)
                new_btn.press()
                await pilot.pause(0.1)

                # Fill in form
                modal.query_one("#agent-form-name", Input).value = "Anthropic Claude Engineer"
                modal.query_one("#agent-form-model", Input).value = "claude-3-5-sonnet"
                modal.query_one("#agent-form-api-key", Input).value = "sk-ant-test-12345"
                modal.query_one("#agent-form-base-url", Input).value = "https://api.anthropic.com/v1"
                modal.query_one("#agent-form-role", Input).value = "Lead Architect"

                # Save agent
                save_btn = modal.query_one("#manager-btn-save", Button)
                save_btn.press()
                await pilot.pause(0.2)

                # Verify agent created in state
                agent_names = [a.name for a in app.state.agents]
                self.assertIn("Anthropic Claude Engineer", agent_names)
                created_agent = next(a for a in app.state.agents if a.name == "Anthropic Claude Engineer")
                self.assertEqual(created_agent.api_key, "sk-ant-test-12345")
                self.assertEqual(created_agent.base_url, "https://api.anthropic.com/v1")

                # Close modal
                close_btn = modal.query_one("#manager-btn-close-top", Button)
                close_btn.press()
                await pilot.pause(0.2)

                # Back to main screen
                self.assertNotIsInstance(app.screen, AgentManagerModal)

    async def test_backend_agent_execution_hook(self):
        import tempfile
        from unittest.mock import AsyncMock, patch

        with tempfile.TemporaryDirectory() as temp_dir:
            app = OriahIDE(root_dir=temp_dir)
            async with app.run_test() as pilot:
                agent_panel = app.query_one("#agent-mode-panel", AgentModePanel)
                with patch.object(app, "_execute_backend_agent", new_callable=AsyncMock) as mock_exec:
                    prompt_input = agent_panel.query_one("#agent-prompt-input")
                    prompt_input.value = "Create test suite for auth"
                    agent_panel._submit_prompt()
                    await pilot.pause(0.2)
                    mock_exec.assert_called_once()
                    agent_arg, prompt_arg = mock_exec.call_args[0]
                    self.assertEqual(prompt_arg, "Create test suite for auth")
                    self.assertEqual(agent_arg.id, app.state.active_agent_id)


if __name__ == "__main__":
    unittest.main()
