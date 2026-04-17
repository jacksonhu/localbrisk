"""Tests for the shell command tool and its runtime bootstrap."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from agent_engine.tools import build_builtin_tools, create_run_command_tool
from agent_engine.tools import shell as shell_module
from agent_engine.tools.shell import ShellRuntimeBootstrap


class TestShellTool:
    def test_create_run_command_tool_bootstraps_environment(self, tmp_path: Path, monkeypatch):
        agent_dir = tmp_path / "agent"
        calls: list[Path] = []

        def fake_ensure_ready(self):
            calls.append(self.agent_path)
            self.agent_path.mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(ShellRuntimeBootstrap, "ensure_ready", fake_ensure_ready)

        tool = create_run_command_tool(agent_path=str(agent_dir))

        assert tool.name == "run_command"
        assert calls == [agent_dir.resolve()]
        assert tool._bootstrap_error is None

    def test_shell_runtime_installs_python_when_missing(self, tmp_path: Path, monkeypatch):
        bootstrap = ShellRuntimeBootstrap(tmp_path / "agent")
        install_calls: list[str] = []

        def fake_find(self):
            if install_calls:
                return Path("/opt/homebrew/bin/python3.13")
            return None

        def fake_install(self):
            install_calls.append("install")

        monkeypatch.setattr(ShellRuntimeBootstrap, "_find_python313_executable", fake_find)
        monkeypatch.setattr(ShellRuntimeBootstrap, "_install_python313", fake_install)

        python_path = bootstrap._ensure_python313()

        assert python_path == Path("/opt/homebrew/bin/python3.13")
        assert install_calls == ["install"]

    def test_run_command_uses_agent_venv_environment(self, tmp_path: Path, monkeypatch):
        agent_dir = tmp_path / "agent"
        scripts_dir = agent_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)

        def fake_ensure_ready(self):
            self.agent_path.mkdir(parents=True, exist_ok=True)
            self._venv_python_path().parent.mkdir(parents=True, exist_ok=True)
            self._venv_python_path().write_text("", encoding="utf-8")

        captured: dict[str, object] = {}

        def fake_run(command, cwd=None, env=None, capture_output=None, text=None, timeout=None, check=None):
            captured["command"] = command
            captured["cwd"] = cwd
            captured["env"] = env
            captured["timeout"] = timeout
            return subprocess.CompletedProcess(command, 0, "ready\n", "")

        monkeypatch.setattr(ShellRuntimeBootstrap, "ensure_ready", fake_ensure_ready)
        monkeypatch.setattr(shell_module.subprocess, "run", fake_run)

        tool = create_run_command_tool(agent_path=str(agent_dir))
        result = tool._run("python --version", path="scripts", timeout_seconds=45)

        expected_venv = agent_dir.resolve() / "venv"
        expected_bin = expected_venv / ("Scripts" if os.name == "nt" else "bin")

        assert captured["cwd"] == str(scripts_dir.resolve())
        assert captured["timeout"] == 45
        assert captured["env"]["VIRTUAL_ENV"] == str(expected_venv)
        assert captured["env"]["PATH"].split(os.pathsep)[0] == str(expected_bin)
        assert captured["command"][-1] == "python --version"
        assert "**Exit code**: 0" in result
        assert "ready" in result

    def test_build_builtin_tools_includes_run_command(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(ShellRuntimeBootstrap, "ensure_ready", lambda self: None)

        tools = build_builtin_tools(agent_path=str(tmp_path / "agent"), task_root=str(tmp_path / ".task"))
        tool_names = [tool.name for tool in tools]

        assert "run_command" in tool_names
