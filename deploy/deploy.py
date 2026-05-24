#!/usr/bin/env python3
"""Deploy BiliRSS to production server

Deploys from local Python package structure to flat server layout.
Transforms relative imports (from .templates...) to flat imports during upload.

Usage:
    python deploy/deploy.py

Config (deploy/deploy_config.py or environment variables):
    SERVER_HOST  — server IP or hostname
    SERVER_USER  — SSH login user  (default: root)
    SERVER_PORT  — SSH port        (default: 22)
    SERVER_PASS  — SSH password    (leave empty to use key-based auth)
    SSH_KEY_PATH — path to private key file (default: ~/.ssh/id_rsa)
"""

import os
import sys
import re
import io
import importlib.util
import time
from pathlib import Path

# ─────────────────────────────────────────────
# Resolve project root (works whether run from
# repo root or from inside deploy/)
# ─────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent          # deploy/
PROJECT_ROOT = SCRIPT_DIR.parent                         # BRSS/

# ─────────────────────────────────────────────
# Deployment config — edit deploy_config.py or
# set environment variables before running.
# ─────────────────────────────────────────────
CONFIG_FILE = SCRIPT_DIR / 'deploy_config.py'

def _load_config():
    """Load config from deploy_config.py if it exists, else use env vars."""
    cfg = {}
    if CONFIG_FILE.exists():
        spec = importlib.util.spec_from_file_location('deploy_config', CONFIG_FILE)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cfg['host']     = getattr(mod, 'SERVER_HOST',  '')
        cfg['user']     = getattr(mod, 'SERVER_USER',  'root')
        cfg['port']     = int(getattr(mod, 'SERVER_PORT', 22))
        cfg['password'] = getattr(mod, 'SERVER_PASS',  '')
        cfg['key_path'] = getattr(mod, 'SSH_KEY_PATH', '')
    # Environment variables override config file
    cfg['host']     = os.environ.get('SERVER_HOST',  cfg.get('host',     ''))
    cfg['user']     = os.environ.get('SERVER_USER',  cfg.get('user',     'root'))
    cfg['port']     = int(os.environ.get('SERVER_PORT', cfg.get('port',  22)))
    cfg['password'] = os.environ.get('SERVER_PASS',  cfg.get('password', ''))
    cfg['key_path'] = os.environ.get('SSH_KEY_PATH', cfg.get('key_path', ''))
    return cfg

# ─────────────────────────────────────────────
# Server-side paths
# ─────────────────────────────────────────────
REMOTE_BASE    = '/opt/bili-rss'
REMOTE_SERVICE = 'bilisrs'

# ─────────────────────────────────────────────
# Local → Remote file mapping
#
# Each entry: (local_path_relative_to_PROJECT_ROOT, remote_path)
# ─────────────────────────────────────────────
FILE_MAP = [
    ('bili_rss/app.py',                  f'{REMOTE_BASE}/app.py'),
    ('bili_rss/templates/index.py',      f'{REMOTE_BASE}/templates_index.py'),
    ('bili_rss/templates/category.py',   f'{REMOTE_BASE}/templates_category.py'),
]

# ─────────────────────────────────────────────
# Import-rewriting rules
#
# Applied to app.py before uploading so that the
# flat-structure server version works without the
# Python package (bili_rss/).
#
# Pattern → Replacement (regex, applied in order)
# ─────────────────────────────────────────────
IMPORT_REWRITES = [
    # from .templates.index import TEMPLATE_INDEX
    # → from templates_index import TEMPLATE_INDEX
    (
        r'from\s+\.templates\.index\s+import\s+',
        'from templates_index import ',
    ),
    # from .templates.category import CATEGORY_DETAIL_TEMPLATE
    # → from templates_category import CATEGORY_DETAIL_TEMPLATE
    (
        r'from\s+\.templates\.category\s+import\s+',
        'from templates_category import ',
    ),
    # Catch-all: any remaining relative import from the package
    # from .something import ... → from something import ...
    (
        r'from\s+\.([\w]+)\s+import\s+',
        r'from \1 import ',
    ),
]


# ══════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════

def _print_step(icon: str, msg: str):
    print(f'\n{icon}  {msg}')

def _print_ok(msg: str):
    print(f'   ✅  {msg}')

def _print_info(msg: str):
    print(f'   ℹ️   {msg}')

def _print_warn(msg: str):
    print(f'   ⚠️   {msg}', file=sys.stderr)

def _print_err(msg: str):
    print(f'   ❌  {msg}', file=sys.stderr)


def _flatten_source(local_path: Path, remote_path: str) -> bytes:
    """
    Read local_path, apply import rewrites when uploading app.py,
    and return the final bytes to upload.
    """
    source = local_path.read_text(encoding='utf-8')

    # Only rewrite imports for app.py
    if local_path.name == 'app.py':
        rewritten = source
        for pattern, replacement in IMPORT_REWRITES:
            new_source = re.sub(pattern, replacement, rewritten)
            if new_source != rewritten:
                # Show what changed
                for line_no, (old_l, new_l) in enumerate(
                    zip(rewritten.splitlines(), new_source.splitlines()), 1
                ):
                    if old_l != new_l:
                        _print_info(f'  rewrite line {line_no}: {old_l.strip()!r}')
                        _print_info(f'               → {new_l.strip()!r}')
                rewritten = new_source
        source = rewritten

    return source.encode('utf-8')


def _connect_ssh(cfg: dict):
    """Return an open paramiko.SSHClient (key or password auth)."""
    try:
        import paramiko
    except ImportError:
        _print_err('paramiko is not installed. Run: pip install paramiko')
        sys.exit(1)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs = dict(
        hostname=cfg['host'],
        port=cfg['port'],
        username=cfg['user'],
        timeout=30,
    )

    if cfg['password']:
        connect_kwargs['password'] = cfg['password']
        auth_hint = 'password'
    else:
        key_path = cfg['key_path'] or os.path.expanduser('~/.ssh/id_rsa')
        if not os.path.exists(key_path):
            _print_err(f'SSH key not found: {key_path}')
            _print_err('Set SERVER_PASS or SSH_KEY_PATH in deploy_config.py')
            sys.exit(1)
        connect_kwargs['key_filename'] = key_path
        auth_hint = f'key ({key_path})'

    _print_info(f'Connecting to {cfg["user"]}@{cfg["host"]}:{cfg["port"]} via {auth_hint} …')
    client.connect(**connect_kwargs)
    return client


def _run_remote(ssh, cmd: str, check: bool = True):
    """Run a command on the remote host, return (stdout, stderr, exit_code)."""
    _, stdout, stderr = ssh.exec_command(cmd)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    if check and exit_code != 0:
        _print_err(f'Remote command failed (exit {exit_code}): {cmd}')
        if err:
            _print_err(err)
        raise RuntimeError(f'Remote command failed: {cmd}')
    return out, err, exit_code


# ══════════════════════════════════════════════
#  Deploy phases
# ══════════════════════════════════════════════

def phase_preflight(cfg: dict):
    """Validate local files and config before touching the server."""
    _print_step('🔍', 'Preflight checks')

    if not cfg['host']:
        _print_err('SERVER_HOST is not set.')
        _print_err(f'Create {CONFIG_FILE} or set the SERVER_HOST environment variable.')
        _print_err('\nExample deploy_config.py:\n')
        _print_err('    SERVER_HOST  = "your_IP"')
        _print_err('    SERVER_USER  = "your_name"')
        _print_err('    SERVER_PORT  = 22')
        _print_err('    SERVER_PASS  = "your_password"   # or leave empty for key auth')
        _print_err('    SSH_KEY_PATH = ""                # e.g. "C:/Users/you/.ssh/id_rsa"')
        sys.exit(1)

    for rel, _ in FILE_MAP:
        p = PROJECT_ROOT / rel
        if not p.exists():
            _print_err(f'Local file not found: {p}')
            sys.exit(1)
        _print_ok(f'Found {rel}')


def phase_upload(ssh, sftp):
    """Flatten & upload all files via SFTP."""
    _print_step('📤', 'Uploading files')

    uploaded = []
    for rel, remote_path in FILE_MAP:
        local_path = PROJECT_ROOT / rel
        _print_info(f'{rel}  →  {remote_path}')

        data = _flatten_source(local_path, remote_path)

        # Write to a temp file first, then atomic-rename
        tmp_path = remote_path + '.deploy_tmp'
        with sftp.file(tmp_path, 'wb') as rf:
            rf.write(data)

        # Rename: effectively atomic on Linux
        _run_remote(ssh, f'mv -f {tmp_path} {remote_path}')
        size_kb = len(data) / 1024
        _print_ok(f'Uploaded {local_path.name} ({size_kb:.1f} KB) → {remote_path}')
        uploaded.append(remote_path)

    return uploaded


def phase_restart(ssh):
    """Restart the systemd service."""
    _print_step('🔄', f'Restarting service: {REMOTE_SERVICE}')
    _run_remote(ssh, f'systemctl restart {REMOTE_SERVICE}')
    # Give the process a moment to settle
    time.sleep(2)
    _print_ok('systemctl restart sent')


def phase_verify(ssh):
    """Verify the service is active and print recent logs."""
    _print_step('🩺', 'Verifying service')

    out, _, exit_code = _run_remote(ssh, f'systemctl is-active {REMOTE_SERVICE}', check=False)
    status = out.strip()

    if status == 'active':
        _print_ok(f'Service is active ✓')
    else:
        _print_err(f'Service status: {status}')
        # Grab the last 30 journal lines to help debug
        logs, _, _ = _run_remote(
            ssh,
            f'journalctl -u {REMOTE_SERVICE} -n 30 --no-pager',
            check=False,
        )
        print('\n─── Last 30 log lines ───')
        print(logs or '(no logs)')
        print('─────────────────────────')
        raise RuntimeError(f'Service {REMOTE_SERVICE} is not active after restart (status={status})')

    # Print last 10 lines for a quick sanity check
    logs, _, _ = _run_remote(
        ssh,
        f'journalctl -u {REMOTE_SERVICE} -n 10 --no-pager',
        check=False,
    )
    if logs:
        print('\n─── Last 10 log lines ───')
        print(logs)
        print('─────────────────────────')

    # Also confirm the remote file timestamps
    out, _, _ = _run_remote(
        ssh,
        f'stat -c "%n  %y  %s bytes" {REMOTE_BASE}/app.py {REMOTE_BASE}/templates_index.py {REMOTE_BASE}/templates_category.py',
        check=False,
    )
    if out:
        print('\n─── Uploaded file stats ───')
        print(out)
        print('───────────────────────────')


# ══════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════

def main():
    print('=' * 60)
    print('  BiliRSS Deploy Script')
    print(f'  Project root : {PROJECT_ROOT}')
    print(f'  Service name : {REMOTE_SERVICE}')
    print(f'  Remote base  : {REMOTE_BASE}')
    print('=' * 60)

    cfg = _load_config()
    t0  = time.time()

    # Phase 0 — preflight (local checks, no network)
    phase_preflight(cfg)

    # Connect SSH
    _print_step('🔌', 'SSH connection')
    ssh = _connect_ssh(cfg)
    sftp = ssh.open_sftp()
    _print_ok(f'Connected to {cfg["host"]}')

    try:
        # Phase 1 — upload
        phase_upload(ssh, sftp)

        # Phase 2 — restart
        phase_restart(ssh)

        # Phase 3 — verify
        phase_verify(ssh)

    except Exception as exc:
        _print_err(f'Deploy failed: {exc}')
        sftp.close()
        ssh.close()
        sys.exit(1)
    finally:
        sftp.close()
        ssh.close()

    elapsed = time.time() - t0
    print('\n' + '=' * 60)
    print(f'  🎉  Deploy complete in {elapsed:.1f}s')
    print('=' * 60)


if __name__ == '__main__':
    main()
