"""GATE TEST: Sandbox read isolation, network denial, memory watchdog.
Must pass before Phase 1 starts.
"""
import json
import os
import shutil
import subprocess
import textwrap
import uuid
from pathlib import Path
import pytest

pytestmark = pytest.mark.gate

PROJECT_ROOT = "/Users/lalithkumargn/Desktop/aicte"
PYTHON = f"{PROJECT_ROOT}/.venv/bin/python3"


def _run_sandboxed(code: str) -> tuple[int, str, str]:
    """Run Python code inside the deny-list sandbox."""
    job_id = uuid.uuid4().hex[:12]
    job_temp = Path(f"/private/tmp/aicte-sbt-{job_id}")
    job_temp.mkdir(mode=0o700)
    try:
        profile = textwrap.dedent(f"""\
            (version 1)
            (deny default)
            (allow process*)
            (allow file-read*)
            (deny file-read*
              (subpath "{PROJECT_ROOT}/secrets")
              (subpath "{PROJECT_ROOT}/data/storage")
              (literal "{PROJECT_ROOT}/.env")
            )
            (allow file-write*
              (subpath "{job_temp}")
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
        (job_temp / "sandbox.sb").write_text(profile)
        (job_temp / "run.py").write_text(code)
        r = subprocess.run(
            ["/usr/bin/sandbox-exec", "-f", str(job_temp / "sandbox.sb"), PYTHON, str(job_temp / "run.py")],
            capture_output=True, text=True, timeout=15)
        return r.returncode, r.stdout, r.stderr
    finally:
        shutil.rmtree(job_temp, ignore_errors=True)


class TestSandboxBasic:
    def test_python_starts(self):
        rc, out, _ = _run_sandboxed("print('OK')")
        assert rc == 0 and "OK" in out

    def test_stdlib_imports(self):
        rc, out, _ = _run_sandboxed("import json,hashlib,os,sys,re; print('STDLIB_OK')")
        assert "STDLIB_OK" in out


class TestSandboxNetwork:
    def test_socket_blocked(self):
        rc, out, _ = _run_sandboxed(textwrap.dedent("""\
            import socket
            try:
                socket.create_connection(('8.8.8.8',53),timeout=2)
                print('ALLOWED')
            except OSError:
                print('BLOCKED')
        """))
        assert "BLOCKED" in out and "ALLOWED" not in out

    def test_dns_blocked(self):
        rc, out, _ = _run_sandboxed(textwrap.dedent("""\
            import socket
            try:
                socket.getaddrinfo('example.com',80)
                print('ALLOWED')
            except (socket.gaierror,OSError):
                print('BLOCKED')
        """))
        assert "BLOCKED" in out


class TestSandboxReadDenied:
    """Sandbox cannot read secrets, storage, or .env (correction #1)."""

    @pytest.fixture(autouse=True)
    def _create_sensitive_files(self):
        Path(f"{PROJECT_ROOT}/secrets").mkdir(exist_ok=True)
        Path(f"{PROJECT_ROOT}/secrets/master.key").write_text("SECRET_KEY_VALUE")
        Path(f"{PROJECT_ROOT}/data/storage").mkdir(parents=True, exist_ok=True)
        Path(f"{PROJECT_ROOT}/data/storage/doc.bin").write_text("encrypted")
        Path(f"{PROJECT_ROOT}/.env").write_text("DB=secret")
        yield
        Path(f"{PROJECT_ROOT}/.env").unlink(missing_ok=True)

    def test_cannot_read_master_key(self):
        rc, out, _ = _run_sandboxed(f"""\
try:
    open('{PROJECT_ROOT}/secrets/master.key').read()
    print('READ')
except (PermissionError,OSError):
    print('BLOCKED')
""")
        assert "BLOCKED" in out and "READ" not in out

    def test_cannot_read_storage(self):
        rc, out, _ = _run_sandboxed(f"""\
try:
    open('{PROJECT_ROOT}/data/storage/doc.bin').read()
    print('READ')
except (PermissionError,OSError):
    print('BLOCKED')
""")
        assert "BLOCKED" in out and "READ" not in out

    def test_cannot_read_env(self):
        rc, out, _ = _run_sandboxed(f"""\
try:
    open('{PROJECT_ROOT}/.env').read()
    print('READ')
except (PermissionError,OSError):
    print('BLOCKED')
""")
        assert "BLOCKED" in out and "READ" not in out


class TestSandboxWriteIsolation:
    def test_cannot_write_outside_temp(self):
        rc, out, _ = _run_sandboxed("""\
try:
    open('/private/tmp/sandbox_escape.txt','w').write('bad')
    print('ESCAPED')
except (PermissionError,OSError):
    print('ISOLATED')
""")
        assert "ISOLATED" in out and "ESCAPED" not in out


class TestMemoryWatchdog:
    def test_kills_on_excess(self):
        """Watchdog kills a subprocess that exceeds memory limit."""
        import sys
        sys.path.insert(0, PROJECT_ROOT)
        from services.sandbox.sandbox_runner import MemoryWatchdog
        import time

        # Use subprocess instead of multiprocessing to avoid pickle issues
        proc = subprocess.Popen(
            [PYTHON, "-c", "x=bytearray(200*1024*1024); import time; time.sleep(30)"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(1)  # let it allocate

        watchdog = MemoryWatchdog(proc.pid, limit_mb=50, interval_s=0.5)
        watchdog.start()
        proc.wait(timeout=10)
        watchdog.stop()

        assert watchdog.killed or proc.returncode != 0
