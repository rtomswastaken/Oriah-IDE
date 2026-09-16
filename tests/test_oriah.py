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
        import tempfile
        self._temp_dir = tempfile.TemporaryDirectory()
        self.state = AppState(root_dir=self._temp_dir.name)

    def tearDown(self):
        self._temp_dir.cleanup()

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
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            app = OriahIDE(root_dir=temp_dir)
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

    async def test_agent_manager_local_models_dropdown_and_back_button(self):
        import tempfile
        from oriah.widgets.agent_manager_modal import AgentManagerModal
        from textual.widgets import Select, Button, Input

        with tempfile.TemporaryDirectory() as temp_dir:
            app = OriahIDE(root_dir=temp_dir)
            async with app.run_test() as pilot:
                app.action_manage_agents()
                await pilot.pause(0.2)
                self.assertIsInstance(app.screen, AgentManagerModal)
                modal = app.screen

                # Verify local models dropdown exists
                local_select = modal.query_one("#agent-form-local-models", Select)
                self.assertIsNotNone(local_select)

                # Verify Back button exists in form actions
                back_btn = modal.query_one("#manager-btn-back", Button)
                self.assertIsNotNone(back_btn)

                # Switch to new agent form
                new_btn = modal.query_one("#manager-btn-new", Button)
                new_btn.press()
                await pilot.pause(0.1)
                self.assertTrue(modal.is_creating_new)

                # Pressing Back button reverts new agent creation
                back_btn.press()
                await pilot.pause(0.1)
                self.assertFalse(modal.is_creating_new)
                self.assertIsInstance(app.screen, AgentManagerModal)

                # Pressing Back button from viewing agent dismisses modal
                back_btn.press()
                await pilot.pause(0.2)
                self.assertNotIsInstance(app.screen, AgentManagerModal)

                # Re-open and test Escape key binding dismisses modal
                app.action_manage_agents()
                await pilot.pause(0.2)
                self.assertIsInstance(app.screen, AgentManagerModal)
                await pilot.press("escape")
                await pilot.pause(0.2)
                self.assertNotIsInstance(app.screen, AgentManagerModal)

    async def test_agent_manager_colorable_glyphs_and_provider_suggestions(self):
        import tempfile
        from oriah.widgets.agent_manager_modal import AgentManagerModal
        from textual.widgets import Select, Button, Input, Label

        with tempfile.TemporaryDirectory() as temp_dir:
            app = OriahIDE(root_dir=temp_dir)
            async with app.run_test() as pilot:
                app.action_manage_agents()
                await pilot.pause(0.2)
                self.assertIsInstance(app.screen, AgentManagerModal)
                modal = app.screen

                # 1. Verify clean glyph filtering
                self.assertEqual(modal._get_clean_glyph("🤖"), "◈")
                self.assertEqual(modal._get_clean_glyph("💎"), "◈")
                self.assertEqual(modal._get_clean_glyph("◆"), "◆")
                self.assertEqual(modal._get_clean_glyph("✦"), "✦")

                # 2. Verify dialog title and buttons contain colorable glyphs
                title = str(modal.query_one("#manager-dialog-title", Label).render())
                self.assertIn("◈", title)
                self.assertNotIn("🤖", title)

                # 3. Test switching provider updates model select options
                provider_select = modal.query_one("#agent-form-provider", Select)
                provider_select.value = "Anthropic"
                await pilot.pause(0.2)
                local_select = modal.query_one("#agent-form-local-models", Select)
                self.assertIn("claude-3-5-sonnet", [val for _, val in local_select._options])

                provider_select.value = "OpenAI"
                await pilot.pause(0.2)
                self.assertIn("gpt-4o", [val for _, val in local_select._options])

    async def test_lead_agent_always_first_and_dynamic_state_updates(self):
        import tempfile
        from oriah.widgets.agent_panel import AgentCardWidget, AgentModePanel

        with tempfile.TemporaryDirectory() as temp_dir:
            app = OriahIDE(root_dir=temp_dir)
            async with app.run_test() as pilot:
                agent_panel = app.query_one("#agent-mode-panel", AgentModePanel)
                await pilot.pause(0.2)

                # 1. Lead agent is ALWAYS first in the card list
                cards = list(agent_panel.query(AgentCardWidget))
                self.assertGreater(len(cards), 0)
                first_card = cards[0]
                self.assertTrue(first_card.is_lead)
                self.assertIn("lead", first_card.agent.role.lower())
                self.assertTrue(first_card.has_class("lead-agent"))

                # 2. Dynamic state updates
                lead_id = first_card.agent.id
                agent_panel.update_agent_status(lead_id, "Thinking")
                await pilot.pause(0.1)
                status_label = first_card.query_one(".agent-card-status")
                self.assertIn("Thinking", str(status_label.render()))
                self.assertTrue(status_label.has_class("status-running"))

                agent_panel.update_agent_status(lead_id, "Tool: patch_file")
                await pilot.pause(0.1)
                self.assertIn("Tool: patch_file", str(status_label.render()))

                agent_panel.reset_all_agent_statuses("Idle")
                await pilot.pause(0.1)
                self.assertIn("Idle", str(status_label.render()))
                self.assertTrue(status_label.has_class("status-idle"))

                # 3. Dynamic subagent spawning
                agent_panel.handle_subagent_spawned("child-sub-99", "researcher")
                await pilot.pause(0.2)
                updated_cards = list(agent_panel.query(AgentCardWidget))
                # Lead agent MUST STILL BE FIRST
                self.assertTrue(updated_cards[0].is_lead)
                self.assertEqual(updated_cards[0].agent.id, lead_id)

                # 4. Switching active agent preserves lead agent at index 0
                second_agent = updated_cards[1].agent
                app.state.active_agent_id = second_agent.id
                agent_panel.refresh_cards()
                await pilot.pause(0.2)
                cards_after_switch = list(agent_panel.query(AgentCardWidget))
                self.assertTrue(cards_after_switch[0].is_lead)
                self.assertEqual(cards_after_switch[0].agent.id, lead_id)


if __name__ == "__main__":
    unittest.main()


