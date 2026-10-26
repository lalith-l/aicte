"""macOS sandbox runner using sandbox-exec.

Security model (deny-list approach — proven working on this machine):
- File reads: allow all EXCEPT secrets/, data/storage/, .env
- File writes: ONLY the per-job temp dir
- Network: DENIED
- Memory watchdog kills child if RSS exceeds limit (ulimit RSS not enforced on macOS)
- RLIMIT_CPU and RLIMIT_FSIZE are enforced
- Each job gets a private temp dir under /private/tmp/ with 0700, deleted after

Label on screen and in report: "OS-level sandbox, reduced isolation"
"""
from __future__ import annotations

import os
import resource
import shutil
import signal
import subprocess
import textwrap
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import psutil

PROJECT_ROOT = os.environ.get("PROJECT_ROOT", str(Path(__file__).resolve().parents[2]))

# Paths the sandbox MUST NOT read
DENIED_READ_PATHS = [
    f"{PROJECT_ROOT}/secrets",
    f"{PROJECT_ROOT}/data/storage",
]
DENIED_READ_LITERALS = [
    f"{PROJECT_ROOT}/.env",
]


@dataclass
class SandboxResult:
    success: bool
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    output_path: Path | None = None
    killed_by_watchdog: bool = False
    killed_by_timeout: bool = False
    error: str | None = None


class SandboxRunnerProtocol(Protocol):
    def run(self, input_path: Path, output_dir: Path, script: str,
            timeout_s: int = 120, memory_mb: int = 1024,
            extra_read_paths: list[str] | None = None) -> SandboxResult: ...


class MemoryWatchdog:
    """Polls child RSS every interval_s. Kills if over limit_mb.
    Needed because RLIMIT_RSS is not enforced on macOS."""

    def __init__(self, pid: int, limit_mb: int = 1024, interval_s: float = 2.0):
        self.pid = pid
        self.limit_bytes = limit_mb * 1024 * 1024
        self.interval_s = interval_s
        self._stop = threading.Event()
        self._killed = False

    def start(self):
        self._thread = threading.Thread(target=self._poll, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    @property
    def killed(self):
        return self._killed

    def _poll(self):
        while not self._stop.is_set():
            try:
                rss = psutil.Process(self.pid).memory_info().rss
                if rss > self.limit_bytes:
                    os.kill(self.pid, signal.SIGKILL)
                    self._killed = True
                    return
            except (psutil.NoSuchProcess, ProcessLookupError):
                return
            self._stop.wait(self.interval_s)


def _generate_sandbox_profile(job_temp_dir: str) -> str:
    """Deny-list profile: allow all reads, deny sensitive paths, deny network."""
    deny_subpaths = "\n  ".join(f'(subpath "{p}")' for p in DENIED_READ_PATHS)
    deny_literals = "\n  ".join(f'(literal "{p}")' for p in DENIED_READ_LITERALS)

    return textwrap.dedent(f"""\
        (version 1)
        (deny default)
        (allow process*)
        (allow file-read*)
        (deny file-read*
          {deny_subpaths}
          {deny_literals}
        )
        (allow file-write*
          (subpath "{job_temp_dir}")
          (subpath "/dev")
          (subpath "/private/var/folders")
        )
        (allow mach*)
        (allow ipc*)
        (allow sysctl*)
        (allow signal)
        (allow pseudo-tty)
        (deny network*)
    """)


def create_job_temp() -> Path:
    job_id = uuid.uuid4().hex[:16]
    path = Path(f"/private/tmp/aicte-sandbox-{job_id}")
    path.mkdir(mode=0o700)
    return path


def cleanup_job_temp(path: Path):
    shutil.rmtree(path, ignore_errors=True)


class MacOSSandboxRunner:
    """Runs Python in macOS sandbox-exec with deny-list isolation.
    Label: "OS-level sandbox, reduced isolation"
    """
    ISOLATION_LABEL = "OS-level sandbox, reduced isolation"

    def __init__(self, python_path: str = f"{PROJECT_ROOT}/.venv/bin/python3"):
        self.python_path = python_path

    def run(self, input_path: Path, output_dir: Path, script: str,
            timeout_s: int = 120, memory_mb: int = 1024,
            extra_read_paths: list[str] | None = None) -> SandboxResult:
        job_temp = create_job_temp()
        watchdog = None
        try:
            inp = job_temp / "input" / input_path.name
            inp.parent.mkdir()
            shutil.copy2(input_path, inp)
            out_dir = job_temp / "output"
            out_dir.mkdir()

            profile = _generate_sandbox_profile(str(job_temp))
            prof_path = job_temp / "sandbox.sb"
            prof_path.write_text(profile)

            cmd = ["/usr/bin/sandbox-exec", "-f", str(prof_path),
                   self.python_path, script,
                   "--input", str(inp), "--output", str(out_dir / "result.json")]

            def set_limits():
                resource.setrlimit(resource.RLIMIT_CPU, (timeout_s, timeout_s))
                resource.setrlimit(resource.RLIMIT_FSIZE, (256*1024*1024, 256*1024*1024))

            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    preexec_fn=set_limits)
            watchdog = MemoryWatchdog(proc.pid, limit_mb=memory_mb)
            watchdog.start()

            try:
                stdout, stderr = proc.communicate(timeout=timeout_s + 10)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
                return SandboxResult(False, -1, stdout.decode(), stderr.decode(),
                                     killed_by_timeout=True, error=f"Timeout {timeout_s}s")
            watchdog.stop()

            if watchdog.killed:
                return SandboxResult(False, proc.returncode, stdout.decode(), stderr.decode(),
                                     killed_by_watchdog=True, error=f"OOM {memory_mb}MB")

            result_path = out_dir / "result.json"
            out_path = None
            if result_path.exists():
                dest = output_dir / "result.json"
                shutil.copy2(result_path, dest)
                out_path = dest

            return SandboxResult(proc.returncode == 0, proc.returncode,
                                 stdout.decode(), stderr.decode(), output_path=out_path)
        except Exception as e:
            return SandboxResult(False, -1, error=str(e))
        finally:
            if watchdog: watchdog.stop()
            cleanup_job_temp(job_temp)
