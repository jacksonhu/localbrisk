"""Shell command tool with automatic Python 3.13 virtual environment bootstrap."""

from __future__ import annotations

import asyncio
import logging
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Sequence, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

PYTHON_VERSION = "3.13"
DEFAULT_TIMEOUT_SECONDS = 120
MAX_OUTPUT_CHARS = 12000


def _truncate_output(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    """Trim oversized command output to keep tool responses readable."""
    normalized = (text or "").strip()
    if len(normalized) <= limit:
        return normalized
    omitted = len(normalized) - limit
    return f"{normalized[:limit]}\n\n... [truncated {omitted} chars]"


def _render_command_result(
    *,
    command: str,
    working_directory: Path,
    exit_code: int,
    stdout: str,
    stderr: str,
    timed_out: bool = False,
) -> str:
    """Render one normalized command execution result."""
    lines = [
        f"**Command**: `{command}`",
        f"**Working directory**: `{working_directory}`",
        f"**Exit code**: {exit_code}",
    ]
    if timed_out:
        lines.append("**Status**: timed out")

    stdout_block = _truncate_output(stdout)
    stderr_block = _truncate_output(stderr)

    if stdout_block:
        lines.extend(["", "**Stdout**:", stdout_block])
    if stderr_block:
        lines.extend(["", "**Stderr**:", stderr_block])
    if not stdout_block and not stderr_block:
        lines.extend(["", "(No output)"])
    return "\n".join(lines)


class RunCommandInput(BaseModel):
    """Input parameters for the run_command tool."""

    command: str = Field(description="Shell command to execute inside the agent workspace")
    path: Optional[str] = Field(
        default=None,
        description="Optional working directory relative to the agent root. Defaults to the agent root itself.",
    )
    timeout_seconds: int = Field(
        default=DEFAULT_TIMEOUT_SECONDS,
        ge=1,
        le=3600,
        description="Maximum command execution time in seconds before timeout.",
    )


class ShellRuntimeBootstrap:
    """Prepare and reuse one agent-local Python 3.13 virtual environment for shell commands."""

    def __init__(self, agent_path: str | Path) -> None:
        self.agent_path = Path(os.path.expanduser(str(agent_path))).resolve()
        self.venv_path = self.agent_path / "venv"

    def ensure_ready(self) -> None:
        """Ensure the agent workspace and its Python 3.13 virtual environment are ready."""
        self.agent_path.mkdir(parents=True, exist_ok=True)
        if self._is_venv_ready():
            logger.info("Reusing shell venv: %s", self.venv_path)
            return

        python_executable = self._ensure_python313()
        self._create_virtualenv(python_executable)
        logger.info("Shell runtime initialized successfully: agent_path=%s venv=%s", self.agent_path, self.venv_path)

    def run_command(self, command: str, path: Optional[str], timeout_seconds: int) -> str:
        """Execute one shell command inside the prepared agent workspace."""
        normalized_command = (command or "").strip()
        if not normalized_command:
            raise ValueError("command cannot be empty")

        working_directory = self.resolve_working_directory(path)
        launch_command = self._build_shell_command(normalized_command)
        env = self.build_command_env()

        logger.info("Executing shell command: cwd=%s command=%s", working_directory, normalized_command)
        try:
            completed = subprocess.run(
                launch_command,
                cwd=str(working_directory),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            logger.warning("Shell command timed out after %ss: %s", timeout_seconds, normalized_command)
            return _render_command_result(
                command=normalized_command,
                working_directory=working_directory,
                exit_code=-1,
                stdout=exc.stdout or "",
                stderr=exc.stderr or "",
                timed_out=True,
            )

        logger.info(
            "Shell command finished: cwd=%s exit_code=%s command=%s",
            working_directory,
            completed.returncode,
            normalized_command,
        )
        return _render_command_result(
            command=normalized_command,
            working_directory=working_directory,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )

    def resolve_working_directory(self, path: Optional[str]) -> Path:
        """Resolve one optional working directory and keep it under the agent workspace."""
        candidate = self.agent_path
        if path:
            raw_path = Path(os.path.expanduser(path.strip()))
            candidate = raw_path if raw_path.is_absolute() else self.agent_path / raw_path

        resolved = candidate.resolve()
        if not resolved.exists():
            raise ValueError(f"working directory does not exist: {resolved}")
        if not resolved.is_dir():
            raise ValueError(f"working directory is not a directory: {resolved}")
        if not resolved.is_relative_to(self.agent_path):
            raise ValueError(f"working directory must stay inside the agent path: {resolved}")
        return resolved

    def build_command_env(self) -> dict[str, str]:
        """Build one environment that prefers the agent-local virtual environment."""
        env = os.environ.copy()
        venv_bin = str(self._venv_bin_path())
        existing_path = env.get("PATH", "")
        env["PATH"] = f"{venv_bin}{os.pathsep}{existing_path}" if existing_path else venv_bin
        env["VIRTUAL_ENV"] = str(self.venv_path)
        env.pop("PYTHONHOME", None)
        return env

    def _ensure_python313(self) -> Path:
        """Locate or install a Python 3.13 interpreter and return its executable path."""
        detected = self._find_python313_executable()
        if detected is not None:
            logger.info("Detected Python %s interpreter: %s", PYTHON_VERSION, detected)
            return detected

        logger.info("Python %s was not found locally, attempting automatic installation", PYTHON_VERSION)
        self._install_python313()

        detected = self._find_python313_executable()
        if detected is None:
            raise RuntimeError(f"Python {PYTHON_VERSION} installation finished but no usable interpreter was found")
        logger.info("Python %s installation succeeded: %s", PYTHON_VERSION, detected)
        return detected

    def _find_python313_executable(self) -> Optional[Path]:
        """Probe common Python launchers and well-known install paths for Python 3.13."""
        candidates: list[Sequence[str]] = []
        if platform.system() == "Windows":
            candidates.append(("py", "-3.13"))
        candidates.extend((("python3.13",), ("python3",), ("python",)))

        seen: set[str] = set()
        for candidate in candidates:
            resolved = self._probe_python_candidate(candidate)
            if resolved is None:
                continue
            resolved_key = str(resolved)
            if resolved_key in seen:
                continue
            seen.add(resolved_key)
            return resolved

        for path_candidate in self._known_python_paths():
            if not path_candidate.exists():
                continue
            resolved = self._probe_python_candidate((str(path_candidate),))
            if resolved is not None:
                return resolved
        return None

    def _probe_python_candidate(self, command: Sequence[str]) -> Optional[Path]:
        """Return the resolved executable when one launcher points to Python 3.13."""
        launcher = command[0]
        if not Path(launcher).is_absolute() and shutil.which(launcher) is None:
            return None

        try:
            completed = subprocess.run(
                [*command, "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}|{sys.executable}')"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except Exception as exc:
            logger.debug("Python launcher probe failed: launcher=%s error=%s", command, exc)
            return None

        if completed.returncode != 0:
            return None

        version, _, executable = (completed.stdout or "").strip().partition("|")
        if version != PYTHON_VERSION or not executable:
            return None
        return Path(executable).resolve()

    def _known_python_paths(self) -> list[Path]:
        """Return platform-specific fallback locations for Python 3.13."""
        system_name = platform.system()
        home = Path.home()
        if system_name == "Darwin":
            return [
                Path("/opt/homebrew/bin/python3.13"),
                Path("/usr/local/bin/python3.13"),
                Path("/opt/homebrew/opt/python@3.13/bin/python3.13"),
                Path("/usr/local/opt/python@3.13/bin/python3.13"),
            ]
        if system_name == "Windows":
            return [
                home / "AppData" / "Local" / "Programs" / "Python" / "Python313" / "python.exe",
                Path("C:/Python313/python.exe"),
            ]
        return [
            Path("/usr/bin/python3.13"),
            Path("/usr/local/bin/python3.13"),
        ]

    def _install_python313(self) -> None:
        """Install Python 3.13 using one supported system package manager."""
        system_name = platform.system()
        if system_name == "Darwin":
            brew_executable = self._detect_brew_executable()
            if brew_executable is None:
                logger.info("Homebrew was not found, attempting automatic Homebrew installation")
                self._run_checked(
                    [
                        "/bin/bash",
                        "-lc",
                        'NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"',
                    ]
                )
                brew_executable = self._detect_brew_executable()
            if brew_executable is None:
                raise RuntimeError("Homebrew installation finished but the brew executable is still unavailable")
            self._run_checked([str(brew_executable), "install", "python@3.13"])
            return

        if system_name == "Linux":
            prefix = self._privileged_prefix()
            if shutil.which("apt-get"):
                self._run_checked([*prefix, "apt-get", "update"])
                self._run_checked([*prefix, "apt-get", "install", "-y", "python3.13", "python3.13-venv"])
                return
            if shutil.which("dnf"):
                self._run_checked([*prefix, "dnf", "install", "-y", "python3.13"])
                return
            if shutil.which("yum"):
                self._run_checked([*prefix, "yum", "install", "-y", "python3.13"])
                return
            raise RuntimeError("Unsupported Linux environment for automatic Python 3.13 installation")

        if system_name == "Windows":
            if shutil.which("winget") is None:
                raise RuntimeError("winget is required for automatic Python 3.13 installation on Windows")
            self._run_checked(
                [
                    "winget",
                    "install",
                    "-e",
                    "--id",
                    "Python.Python.3.13",
                    "--silent",
                    "--accept-package-agreements",
                    "--accept-source-agreements",
                ]
            )
            return

        raise RuntimeError(f"Unsupported operating system for automatic Python 3.13 installation: {system_name}")

    def _detect_brew_executable(self) -> Optional[Path]:
        """Locate the Homebrew executable from PATH or standard macOS install paths."""
        candidates = [shutil.which("brew"), "/opt/homebrew/bin/brew", "/usr/local/bin/brew"]
        for candidate in candidates:
            if not candidate:
                continue
            path = Path(candidate)
            if path.exists():
                return path.resolve()
        return None

    def _privileged_prefix(self) -> list[str]:
        """Return an optional privilege escalation prefix for package manager commands."""
        geteuid = getattr(os, "geteuid", None)
        if callable(geteuid) and geteuid() == 0:
            return []
        if shutil.which("sudo"):
            return ["sudo", "-n"]
        return []

    def _create_virtualenv(self, python_executable: Path) -> None:
        """Create or repair the agent-local virtual environment with Python 3.13."""
        if self.venv_path.exists() and not self._is_venv_ready():
            logger.warning("Removing broken shell venv before recreation: %s", self.venv_path)
            shutil.rmtree(self.venv_path, ignore_errors=True)

        if self._is_venv_ready():
            return

        self._run_checked([str(python_executable), "-m", "venv", str(self.venv_path)], cwd=str(self.agent_path))
        if not self._is_venv_ready():
            raise RuntimeError(f"Virtual environment creation finished but venv is still invalid: {self.venv_path}")
        logger.info("Created shell venv: %s", self.venv_path)

    def _is_venv_ready(self) -> bool:
        """Check whether the agent-local virtual environment looks usable."""
        return self._venv_python_path().exists()

    def _venv_bin_path(self) -> Path:
        """Return the executable directory inside the virtual environment."""
        return self.venv_path / ("Scripts" if platform.system() == "Windows" else "bin")

    def _venv_python_path(self) -> Path:
        """Return the Python executable path inside the virtual environment."""
        executable_name = "python.exe" if platform.system() == "Windows" else "python"
        return self._venv_bin_path() / executable_name

    def _build_shell_command(self, command: str) -> list[str]:
        """Wrap one raw command in the platform-appropriate shell launcher."""
        if platform.system() == "Windows":
            return ["cmd", "/c", command]
        return ["/bin/bash", "-lc", command]

    def _run_checked(self, command: Sequence[str], cwd: Optional[str] = None) -> None:
        """Execute one bootstrap command and raise a detailed error on failure."""
        logger.info("Running bootstrap command: %s", " ".join(command))
        completed = subprocess.run(
            list(command),
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=1800,
            check=False,
        )
        if completed.returncode == 0:
            return

        stdout = _truncate_output(completed.stdout)
        stderr = _truncate_output(completed.stderr)
        raise RuntimeError(
            "Bootstrap command failed: "
            f"{' '.join(command)}\n"
            f"Exit code: {completed.returncode}\n"
            f"Stdout: {stdout or '(empty)'}\n"
            f"Stderr: {stderr or '(empty)'}"
        )


class RunCommandTool(BaseTool):
    """Run shell commands inside the agent workspace using the agent-local Python virtual environment."""

    name: str = "run_command"
    description: str = (
        "Execute shell commands inside the configured agent workspace. The tool automatically ensures a local "
        "Python 3.13 interpreter and an agent-local venv before command execution."
    )
    args_schema: Type[BaseModel] = RunCommandInput

    _agent_path: Optional[str] = None
    _runtime: Optional[ShellRuntimeBootstrap] = None
    _bootstrap_error: Optional[str] = None

    def ensure_environment_ready(self) -> None:
        """Prepare the shell runtime once and cache any bootstrap error for later reporting."""
        if not self._agent_path:
            self._bootstrap_error = "run_command requires a configured agent_path"
            logger.error(self._bootstrap_error)
            return

        if self._runtime is None:
            self._runtime = ShellRuntimeBootstrap(self._agent_path)

        try:
            self._runtime.ensure_ready()
            self._bootstrap_error = None
        except Exception as exc:
            self._bootstrap_error = str(exc)
            logger.error("Failed to initialize shell runtime for %s: %s", self._agent_path, exc)

    def _run(self, command: str, path: Optional[str] = None, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> str:
        self.ensure_environment_ready()
        if self._bootstrap_error:
            return f"❌ Failed to initialize shell runtime\nError: {self._bootstrap_error}"
        if self._runtime is None:
            return "❌ Failed to initialize shell runtime\nError: Missing runtime bootstrap"

        try:
            return self._runtime.run_command(command=command, path=path, timeout_seconds=timeout_seconds)
        except Exception as exc:
            logger.error("Failed to run shell command '%s': %s", command, exc, exc_info=True)
            return f"❌ Failed to run command\nError: {exc}"

    async def _arun(self, command: str, path: Optional[str] = None, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> str:
        return await asyncio.to_thread(self._run, command, path, timeout_seconds)


def create_run_command_tool(agent_path: Optional[str] = None) -> RunCommandTool:
    """Create a run_command tool bound to one agent workspace."""
    tool = RunCommandTool()
    tool._agent_path = agent_path
    tool.ensure_environment_ready()
    return tool


__all__ = [
    "RunCommandInput",
    "RunCommandTool",
    "ShellRuntimeBootstrap",
    "create_run_command_tool",
]
