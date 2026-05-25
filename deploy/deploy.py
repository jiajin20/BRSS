#!/usr/bin/env python3
"""
BiliRSS 部署工具 — 交互式菜单

11 项功能：
  1.首次部署  2.更新代码  3.启动服务  4.停止服务  5.重启服务
  6.查看状态  7.查看日志  8.卸载服务  9.查看密钥  10.修改密钥
  0.退出

部署流程：git clone → 扁平化上传 → 推送 → 清理本地仓库
首次部署自动检查并安装缺失的 Python 依赖
密钥管理：查看/修改 app.py 中的 DELETE_SECRET_KEY（删除音频文件的密码），修改后自动重启服务
"""

import os
import sys
import re
import time
import base64
import shutil
import subprocess
import configparser as _cp
from pathlib import Path

# ═══════════════════════════════════════════════
# 路径（py 脚本和打包后的 exe 均适用）
# config.ini 始终与 deploy.py 或 BiliRSS-Deploy.exe 放在同一目录
# ═══════════════════════════════════════════════
def _exe_dir():
    """返回 exe/脚本 所在目录（PyInstaller 下用 sys.executable）"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

SCRIPT_DIR   = _exe_dir()
PROJECT_ROOT = SCRIPT_DIR.parent if (SCRIPT_DIR / '..' / 'bili_rss').exists() else SCRIPT_DIR
CONFIG_FILE  = SCRIPT_DIR / 'config.ini'        # 统一配置文件
TEMP_CLONE   = SCRIPT_DIR / '__deploy_clone__'

# ═══════════════════════════════════════════════
# 配置加载（仅 INI 格式）
# ═══════════════════════════════════════════════
import configparser as _cp

def _create_default_config():
    """创建默认 config.ini"""
    default = '''[BiliRSS Deploy]
# 服务器连接
SERVER_HOST = 192.168.124.20
SERVER_USER = root
SERVER_PORT = 22
SERVER_PASS =
SSH_KEY_PATH =

# 应用配置
APP_PORT = 5000
REPO_URL = https://gitee.com/jiajin0920/BRSS.git
LOCAL_REPO =
REMOTE_BASE = /opt/bili-rss
SERVICE_NAME = bilisrs
'''
    CONFIG_FILE.write_text(default, encoding='utf-8')
    return default


def _load_config():
    """读取 config.ini。不存在则自动创建默认配置。环境变量可覆盖。"""
    cfg = {
        'host':        '',
        'user':        'root',
        'port':        22,
        'password':    '',
        'key_path':    '',
        'app_port':    5000,
        'repo_url':    'https://gitee.com/jiajin0920/BRSS.git',
        'remote_base': '/opt/bili-rss',
        'service':     'bilisrs',
        'local_repo':  '',
    }

    if not CONFIG_FILE.exists():
        _create_default_config()
        print('   ℹ️  已创建默认 config.ini，请编辑后重新运行')
        # 只返回默认值，让用户编辑后再运行
        # 环境变量仍然可以覆盖
        _apply_env_overrides(cfg)
        return cfg

    cp = _cp.ConfigParser()
    cp.read(CONFIG_FILE, encoding='utf-8')
    section = 'BiliRSS Deploy'

    if cp.has_section(section):
        get = lambda k, d='': cp.get(section, k, fallback=d)
        cfg['host']        = get('SERVER_HOST').strip()
        cfg['user']        = get('SERVER_USER', 'root').strip()
        cfg['port']        = int(get('SERVER_PORT', '22').strip())
        cfg['password']    = get('SERVER_PASS').strip()
        cfg['key_path']    = get('SSH_KEY_PATH').strip()
        cfg['app_port']    = int(get('APP_PORT', '5000').strip())
        cfg['repo_url']    = get('REPO_URL', 'https://gitee.com/jiajin0920/BRSS.git').strip()
        cfg['remote_base'] = get('REMOTE_BASE', '/opt/bili-rss').strip()
        cfg['service']     = get('SERVICE_NAME', 'bilisrs').strip()
        cfg['local_repo']  = get('LOCAL_REPO').strip()

    _apply_env_overrides(cfg)
    return cfg


def _apply_env_overrides(cfg):
    """环境变量覆盖配置"""
    if os.environ.get('SERVER_HOST'):    cfg['host']     = os.environ['SERVER_HOST']
    if os.environ.get('SERVER_USER'):    cfg['user']     = os.environ['SERVER_USER']
    if os.environ.get('SERVER_PORT'):    cfg['port']     = int(os.environ['SERVER_PORT'])
    if os.environ.get('SERVER_PASS'):    cfg['password'] = os.environ['SERVER_PASS']
    if os.environ.get('SSH_KEY_PATH'):   cfg['key_path'] = os.environ['SSH_KEY_PATH']


# ═══════════════════════════════════════════════
# 文件映射 + import 重写
# ═══════════════════════════════════════════════
REMOTE_BASE    = '/opt/bili-rss'

FILE_MAP = [
    ('bili_rss/app.py',                f'{REMOTE_BASE}/app.py'),
    ('bili_rss/templates/index.py',    f'{REMOTE_BASE}/templates_index.py'),
    ('bili_rss/templates/category.py', f'{REMOTE_BASE}/templates_category.py'),
]

IMPORT_REWRITES = [
    (r'from\s+\.templates\.index\s+import\s+',    'from templates_index import '),
    (r'from\s+\.templates\.category\s+import\s+', 'from templates_category import '),
    (r'from\s+\.([\w]+)\s+import\s+',             r'from \1 import '),
]

# ═══════════════════════════════════════════════
# 进度显示
# ═══════════════════════════════════════════════
_spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

class Spinner:
    """终端旋转动画"""
    def __init__(self, msg):
        self.msg = msg
        self._i = 0
        self._running = False
        self._start = 0

    def start(self):
        self._running = True
        self._start = time.time()
        self._tick()

    def _tick(self):
        if not self._running:
            return
        elapsed = int(time.time() - self._start)
        m, s = divmod(elapsed, 60)
        char = _spinner[self._i % len(_spinner)]
        sys.stdout.write(f'\r   {char} {self.msg}… ({m:02d}:{s:02d})')
        sys.stdout.flush()
        self._i += 1

    def update(self, msg):
        self.msg = msg

    def done(self, ok=True):
        self._running = False
        icon = '✅' if ok else '❌'
        elapsed = int(time.time() - self._start)
        m, s = divmod(elapsed, 60)
        sys.stdout.write(f'\r   {icon} {self.msg} ({m:02d}:{s:02d})\n')
        sys.stdout.flush()

    def fail(self, msg):
        self._running = False
        sys.stdout.write(f'\r   ❌ {msg}\n')
        sys.stdout.flush()


# ═══════════════════════════════════════════════
# 打印辅助
# ═══════════════════════════════════════════════
def _step(msg):     print(f'\n🔹 {msg}')
def _ok(msg):       print(f'   ✅ {msg}')
def _info(msg):     print(f'   ℹ️  {msg}')
def _warn(msg):     print(f'   ⚠️  {msg}', file=sys.stderr)
def _err(msg):      print(f'   ❌ {msg}', file=sys.stderr)

# ═══════════════════════════════════════════════
# SSH
# ═══════════════════════════════════════════════
def _connect_ssh(cfg):
    try:
        import paramiko
    except ImportError:
        _err('缺少 paramiko，请运行：pip install paramiko')
        sys.exit(1)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    kwargs = dict(hostname=cfg['host'], port=cfg['port'], username=cfg['user'], timeout=30)
    if cfg['password']:
        kwargs['password'] = cfg['password']
        hint = '密码'
    else:
        key = cfg['key_path'] or os.path.expanduser('~/.ssh/id_rsa')
        if not os.path.exists(key):
            _err(f'SSH 密钥不存在: {key}')
            _err('请在 config.ini 中设置 SERVER_PASS 或 SSH_KEY_PATH')
            sys.exit(1)
        kwargs['key_filename'] = key
        hint = f'密钥({key})'

    _info(f'连接 {cfg["user"]}@{cfg["host"]}:{cfg["port"]} ({hint}) …')
    client.connect(**kwargs)
    _ok(f'已连接 {cfg["host"]}')
    return client


def _run(ssh, cmd, check=True, progress_msg=None):
    """执行远程命令，可选显示 spinner"""
    sp = None
    if progress_msg:
        sp = Spinner(progress_msg)
        sp.start()

    _, stdout, stderr = ssh.exec_command(cmd)

    # 等待命令执行完毕，同时更新 spinner
    while not stdout.channel.exit_status_ready():
        if sp:
            sp._tick()
        time.sleep(0.15)

    code = stdout.channel.recv_exit_status()
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()

    if sp:
        sp.done(ok=(code == 0 if check else True))

    if check and code != 0:
        if err:
            _err(err[-500:])
        raise RuntimeError(f'远程命令失败 (exited {code})')
    return out, err, code


# ═══════════════════════════════════════════════
# Git 操作
# ═══════════════════════════════════════════════
def _git_clone(cfg, force=True):
    """克隆仓库到临时目录。force=True 时先删除已有目录"""
    repo_url = cfg['repo_url']
    if not repo_url:
        _err('未配置 REPO_URL')
        return None

    _step('拉取仓库代码')

    if TEMP_CLONE.exists() and force:
        _info('清除已有本地仓库 …')
        shutil.rmtree(TEMP_CLONE, ignore_errors=True)
        time.sleep(0.5)

    if TEMP_CLONE.exists():
        # 已有仓库，执行 git pull
        _info('已有本地仓库，执行 git pull …')
        sp = Spinner('git pull')
        sp.start()
        try:
            result = subprocess.run(
                ['git', 'pull', '--ff-only'],
                cwd=TEMP_CLONE, capture_output=True, text=True, timeout=120
            )
            sp.done(ok=(result.returncode == 0))
            if result.returncode != 0:
                _warn(f'git pull 失败: {result.stderr.strip()}')
                _info('尝试重新 clone …')
                shutil.rmtree(TEMP_CLONE, ignore_errors=True)
                return _git_clone(cfg, force=True)
        except Exception:
            sp.fail('git pull 异常')
            return None
    else:
        # 全新 clone
        sp = Spinner(f'git clone {repo_url}')
        sp.start()
        try:
            result = subprocess.run(
                ['git', 'clone', '--depth', '1', repo_url, str(TEMP_CLONE)],
                capture_output=True, text=True, timeout=120
            )
            sp.done(ok=(result.returncode == 0))
            if result.returncode != 0:
                _err(f'git clone 失败: {result.stderr.strip()}')
                return None
        except subprocess.TimeoutExpired:
            sp.fail('git clone 超时')
            return None
        except Exception as e:
            sp.fail(f'git clone 异常: {e}')
            return None

    _ok(f'仓库就绪: {TEMP_CLONE}')
    return TEMP_CLONE


def _cleanup_clone():
    """删除本地临时仓库"""
    if TEMP_CLONE.exists():
        _step('清理本地仓库')
        sp = Spinner('删除临时仓库')
        sp.start()
        shutil.rmtree(TEMP_CLONE, ignore_errors=True)
        time.sleep(0.3)
        sp.done()


# ═══════════════════════════════════════════════
# 源文件展平
# ═══════════════════════════════════════════════
def _flatten(local_path):
    """读取源文件并重写相对 import 为扁平 import"""
    source = local_path.read_text(encoding='utf-8')
    if local_path.name == 'app.py':
        for pat, repl in IMPORT_REWRITES:
            source = re.sub(pat, repl, source)
    return source.encode('utf-8')


# ═══════════════════════════════════════════════
# 依赖检查与安装
# ═══════════════════════════════════════════════
def _check_and_install_deps(ssh, cfg):
    """检查服务器上 requirements.txt 中的包，自动安装缺失的"""
    req_file = TEMP_CLONE / 'requirements.txt'
    if not req_file.exists():
        _info('未找到 requirements.txt，跳过依赖检查')
        return

    _step('检查服务器 Python 依赖')
    required = [line.strip() for line in req_file.read_text(encoding='utf-8').splitlines()
                if line.strip() and not line.strip().startswith('#')]
    if not required:
        _info('requirements.txt 为空')
        return

    missing = []
    total = len(required)
    for i, pkg_line in enumerate(required):
        pkg_name = re.split(r'[<>=!~]', pkg_line)[0].strip()
        out, _, code = _run(ssh, f'pip3 show {pkg_name} 2>/dev/null || pip show {pkg_name} 2>/dev/null', check=False)
        status = '✅' if code == 0 else '❌ 缺失'
        print(f'   [{i+1}/{total}] {pkg_line:30s} {status}')
        if code != 0:
            missing.append(pkg_line)

    if missing:
        _warn(f'发现 {len(missing)} 个缺失的包，开始安装 …')
        for pkg in missing:
            sp = Spinner(f'pip install {pkg}')
            sp.start()
            out, err, code = _run(ssh, f'pip3 install {pkg} 2>&1 || pip install {pkg} 2>&1', check=False)
            sp.done(ok=(code == 0))
            if code != 0:
                _err(f'安装失败: {pkg}')
                if err:
                    _err(err[-200:])
                # 继续安装下一个，不中断
        _ok('依赖安装完成')
    else:
        _ok('所有依赖已安装 ✓')


# ═══════════════════════════════════════════════
# 文件上传
# ═══════════════════════════════════════════════
def _upload_files(ssh, sftp, cfg, clone_path):
    """从 clone 目录上传所有文件到服务器（带进度）"""
    _step('上传文件到服务器')
    rb = cfg['remote_base']

    for rel, remote_tmpl in FILE_MAP:
        remote_path = remote_tmpl.replace(REMOTE_BASE, rb)
        local = clone_path / rel
        if not local.exists():
            _warn(f'文件不存在: {rel}')
            continue

        sp = Spinner(f'上传 {rel}')
        sp.start()
        try:
            data = _flatten(local)
            tmp = remote_path + '.deploy_tmp'
            with sftp.file(tmp, 'wb') as f:
                f.write(data)
            _run(ssh, f'mv -f {tmp} {remote_path}', check=True)
            sp.update(f'{rel} ({len(data)/1024:.1f} KB)')
            sp.done(ok=True)
        except Exception as e:
            sp.fail(f'{rel} 上传失败: {e}')
            raise


# ═══════════════════════════════════════════════
# Systemd unit
# ═══════════════════════════════════════════════
SYSTEMD_UNIT = '''[Unit]
Description=BiliRSS Audio RSS Server
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={remote_base}
Environment="BILI_RSS_BASE_URL={base_url}"
ExecStart=/usr/bin/python3 {remote_base}/app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
'''

# ═══════════════════════════════════════════════
# 验证
# ═══════════════════════════════════════════════
def _verify(ssh, cfg):
    _step('验证服务')
    out, _, code = _run(ssh, f'systemctl is-active {cfg["service"]}', check=False)
    status = out.strip()
    if status == 'active':
        _ok('服务运行正常 ✓')
        logs, _, _ = _run(ssh, f'journalctl -u {cfg["service"]} -n 5 --no-pager', check=False)
        if logs:
            print('\n─── 最近日志 ───')
            print(logs)
            print('────────────────')
    else:
        _err(f'服务状态异常: {status}')
        logs, _, _ = _run(ssh, f'journalctl -u {cfg["service"]} -n 20 --no-pager', check=False)
        if logs:
            print('\n─── 最近日志 ───')
            print(logs)
            print('────────────────')


def _show_status(ssh, cfg):
    svc = cfg['service']
    out, _, _ = _run(ssh, f'systemctl is-active {svc}', check=False)
    status = out.strip()
    icon = '🟢' if status == 'active' else '🔴'
    print(f'   {icon} 服务状态: {status}')

    out, _, _ = _run(ssh, f'ss -tlnp | grep :{cfg["app_port"]} || true', check=False)
    if out:
        print(f'   📡 端口 {cfg["app_port"]}: 正在监听')
    else:
        print(f'   ⚠️  端口 {cfg["app_port"]}: 未监听')

    out, _, _ = _run(ssh, f'df -h {cfg["remote_base"]} | tail -1 | awk \'{{print $3"/"$2" ("$5")"}}\'', check=False)
    if out:
        print(f'   💾 磁盘: {out}')

# ═══════════════════════════════════════════════
# 菜单操作 1-8（继承原有）
# ═══════════════════════════════════════════════

def do_first_deploy(ssh, sftp, cfg):
    """首次部署：git clone → 上传 → 检查依赖 → 写 systemd → 启动 → 清理"""
    _step('首次部署')
    rb = cfg['remote_base']
    svc = cfg['service']
    base_url = f'http://{cfg["host"]}:{cfg["app_port"]}'

    # 1. Git clone
    clone_path = _git_clone(cfg, force=True)
    if not clone_path:
        _err('无法获取代码，终止部署')
        return

    try:
        # 2. 创建远程目录
        _info('创建远程目录 …')
        _run(ssh, f'mkdir -p {rb}/audio {rb}/meta {rb}/rss {rb}/cookies {rb}/covers')
        _ok('目录创建完成')

        # 3. 上传文件
        _upload_files(ssh, sftp, cfg, clone_path)

        # 4. 检查并安装依赖
        _check_and_install_deps(ssh, cfg)

        # 5. 创建 systemd 服务
        _info(f'创建 systemd 服务: {svc}')
        unit = SYSTEMD_UNIT.format(user=cfg['user'], remote_base=rb, base_url=base_url)
        # 用 sftp 写文件更可靠，避免 heredoc 转义问题
        with sftp.file(f'/etc/systemd/system/{svc}.service', 'w') as f:
            f.write(unit)
        _run(ssh, 'systemctl daemon-reload')
        _ok('systemd 服务已创建')

        # 6. 启动
        _info('启动服务 …')
        _run(ssh, f'systemctl enable {svc}')
        _run(ssh, f'systemctl restart {svc}', progress_msg='等待服务启动')
        time.sleep(2)

        # 7. 验证
        _verify(ssh, cfg)

    finally:
        _cleanup_clone()


def do_update_code(ssh, sftp, cfg):
    """更新代码：git clone → 上传 → 重启 → 验证 → 清理"""
    _step('更新代码')

    clone_path = _git_clone(cfg, force=True)
    if not clone_path:
        _err('无法获取代码，终止更新')
        return

    try:
        _upload_files(ssh, sftp, cfg, clone_path)
        _run(ssh, f'systemctl restart {cfg["service"]}')
        time.sleep(2)
        _ok('代码已更新并重启')
        _verify(ssh, cfg)
    finally:
        _cleanup_clone()


def do_start(ssh, cfg):
    _step('启动服务')
    _run(ssh, f'systemctl start {cfg["service"]}')
    _ok('服务已启动')
    _show_status(ssh, cfg)


def do_stop(ssh, cfg):
    _step('停止服务')
    _run(ssh, f'systemctl stop {cfg["service"]}')
    _ok('服务已停止')


def do_restart(ssh, cfg):
    _step('重启服务')
    _run(ssh, f'systemctl restart {cfg["service"]}')
    time.sleep(2)
    _ok('服务已重启')
    _show_status(ssh, cfg)


def do_status(ssh, cfg):
    _step('服务状态')
    _show_status(ssh, cfg)


def do_logs(ssh, cfg):
    _step('最近日志（30 行）')
    out, _, _ = _run(ssh, f'journalctl -u {cfg["service"]} -n 30 --no-pager', check=False)
    print(out or '(无日志)')
    print('─' * 50)


def do_uninstall(ssh, cfg):
    _step('卸载服务')
    svc = cfg['service']
    rb = cfg['remote_base']

    confirm = input(f'\n⚠️  确认要卸载 {svc} 并删除 {rb} 吗？输入 "yes" 确认: ').strip()
    if confirm.lower() != 'yes':
        _info('已取消')
        return

    _run(ssh, f'systemctl stop {svc}', check=False)
    _run(ssh, f'systemctl disable {svc}', check=False)
    _run(ssh, f'rm -f /etc/systemd/system/{svc}.service', check=False)
    _run(ssh, 'systemctl daemon-reload', check=False)
    _run(ssh, f'rm -rf {rb}', check=False)
    _ok(f'已卸载: {svc}\n   已删除: {rb}')

# ═══════════════════════════════════════════════
# 菜单操作 9-10：删除密钥管理（app.py 中的 DELETE_SECRET_KEY）
# ═══════════════════════════════════════════════

def do_view_key(ssh, cfg):
    """查看服务器上当前的删除密钥（DELETE_SECRET_KEY）"""
    _step('查看删除密钥')
    rb = cfg['remote_base']
    app_py = f'{rb}/app.py'

    # 检查文件是否存在
    out, _, code = _run(ssh, f'test -f {app_py} && echo OK || echo MISSING', check=False)
    if 'MISSING' in out:
        _err(f'服务器上未找到 {app_py}')
        return

    # 读取 DELETE_SECRET_KEY 行
    out, _, code = _run(ssh,
        f"python3 -c \"import re; c=open('{app_py}').read(); m=re.search(r\\\"DELETE_SECRET_KEY\\\\s*=\\\\s*'([^']*)'\\\", c); print(m.group(1) if m else 'NOT_FOUND')\"",
        check=False)

    if code != 0 or 'NOT_FOUND' in out:
        _err('无法读取密钥，app.py 中可能不存在 DELETE_SECRET_KEY')
        return

    key = out.strip()
    print(f'   🔑 当前删除密钥:')
    print(f'      {key}')
    print()
    print(f'   ℹ️  此密钥用于删除音频文件时的身份验证')
    print(f'   ℹ️  修改密钥后需重启服务才能生效')


def do_modify_key(ssh, sftp, cfg):
    """修改服务器上 app.py 中的 DELETE_SECRET_KEY 并重启服务"""
    _step('修改删除密钥')
    rb = cfg['remote_base']
    svc = cfg['service']
    app_py = f'{rb}/app.py'

    # 先显示当前密钥（前8后4，中间用*）
    out, _, code = _run(ssh,
        f"python3 -c \"import re; c=open('{app_py}').read(); m=re.search(r\\\"DELETE_SECRET_KEY\\\\s*=\\\\s*'([^']*)'\\\", c); print(m.group(1) if m else 'NOT_FOUND')\"",
        check=False)

    if code != 0 or 'NOT_FOUND' in out:
        _err('无法读取密钥，app.py 中可能不存在 DELETE_SECRET_KEY')
        return

    old_key = out.strip()
    if len(old_key) > 12:
        masked = old_key[:8] + '*' * (len(old_key) - 12) + old_key[-4:]
    else:
        masked = old_key[:4] + '*' * max(0, len(old_key) - 4)
    print(f'   当前密钥: {masked}')
    print()

    new_key = input('   请输入新的删除密钥（留空取消）: ').strip()
    if not new_key:
        _info('已取消')
        return

    if len(new_key) < 8:
        _warn('密钥长度建议不少于 8 位，确认继续？')
        confirm = input('   输入 y 确认: ').strip().lower()
        if confirm != 'y':
            _info('已取消')
            return

    # 用 base64 + SFTP 临时脚本安全传递密钥（避免 shell 特殊字符问题）
    _step('更新密钥')
    sp = Spinner('正在更新服务器上的密钥')
    sp.start()

    encoded_key = base64.b64encode(new_key.encode()).decode()
    tmp_script = f'{rb}/.deploy_update_key.py'

    script = f'''import re, base64
new_key = base64.b64decode("{encoded_key}").decode()
with open("{app_py}", "r") as f:
    c = f.read()
c = re.sub(r"DELETE_SECRET_KEY\\s*=\\s*'[^']*'", "DELETE_SECRET_KEY = '" + new_key + "'", c)
with open("{app_py}", "w") as f:
    f.write(c)
print("OK")
'''

    try:
        with sftp.file(tmp_script, 'w') as f:
            f.write(script)
        out, err, code = _run(ssh, f'python3 {tmp_script}', check=False)
        sp.done(ok=(code == 0 and 'OK' in out))

        if code != 0 or 'OK' not in out:
            _err('密钥更新失败')
            if err:
                _err(err[-300:])
            return
    finally:
        _run(ssh, f'rm -f {tmp_script}', check=False)

    _ok('密钥已更新')

    # 重启服务
    _step('重启服务使密钥生效')
    sp = Spinner('重启服务')
    sp.start()
    _run(ssh, f'systemctl restart {svc}', check=False)
    time.sleep(2)
    out, _, code = _run(ssh, f'systemctl is-active {svc}', check=False)
    sp.done(ok=(out.strip() == 'active'))

    if out.strip() == 'active':
        _ok('服务已重启，新密钥已生效 ✓')
    else:
        _err(f'服务状态异常: {out.strip()}')

# ═══════════════════════════════════════════════
# 主菜单
# ═══════════════════════════════════════════════

BANNER = '''════════════════════════════════════════
  BiliRSS 部署工具
════════════════════════════════════════
  1. 首次部署          6. 查看状态
  2. 更新代码          7. 查看日志
  3. 启动服务          8. 卸载服务
  4. 停止服务          9. 查看密钥
  5. 重启服务         10. 修改密钥
                       0. 退出
════════════════════════════════════════'''

MENU_DISPLAY = {
    '1':  ('首次部署',    do_first_deploy, True),
    '2':  ('更新代码',    do_update_code,  True),
    '3':  ('启动服务',    do_start,        True),
    '4':  ('停止服务',    do_stop,         True),
    '5':  ('重启服务',    do_restart,      True),
    '6':  ('查看状态',    do_status,       True),
    '7':  ('查看日志',    do_logs,         True),
    '8':  ('卸载服务',    do_uninstall,    True),
    '9':  ('查看密钥',    do_view_key,     True),
    '10': ('修改密钥',    do_modify_key,   True),
}


def main():
    cfg = _load_config()

    if not cfg['host']:
        _err('未配置 SERVER_HOST，请编辑 config.ini 后再运行')
        _err(f'配置文件位置: {CONFIG_FILE}')
        sys.exit(1)

    # 需要 SSH 的选项才先连接；查看/修改密钥不需要
    ssh = None
    sftp = None

    def ensure_ssh():
        nonlocal ssh, sftp
        if ssh is not None:
            return True
        try:
            ssh = _connect_ssh(cfg)
            sftp = ssh.open_sftp()
            return True
        except Exception as e:
            _err(f'SSH 连接失败: {e}')
            return False

    try:
        while True:
            print()
            print(BANNER)
            print(f'\n目标: {cfg["user"]}@{cfg["host"]}:{cfg["port"]}')
            print(f'端口: {cfg["app_port"]}  路径: {cfg["remote_base"]}  服务: {cfg["service"]}')
            choice = input('\n请选择 [0-10]: ').strip()

            if choice == '0':
                print('已退出')
                break
            elif choice in MENU_DISPLAY:
                name, func, needs_ssh = MENU_DISPLAY[choice]
                if needs_ssh and not ensure_ssh():
                    continue

                try:
                    if needs_ssh:
                        if func.__code__.co_argcount == 3:  # (ssh, sftp, cfg)
                            func(ssh, sftp, cfg)
                        else:
                            func(ssh, cfg)
                    else:
                        func(cfg)
                except Exception as e:
                    _err(f'操作失败: {e}')
                    import traceback
                    traceback.print_exc()
            else:
                _warn('无效选择，请输入 0-10')
    finally:
        if sftp:
            sftp.close()
        if ssh:
            ssh.close()
        # 确保清理临时仓库
        _cleanup_clone()


if __name__ == '__main__':
    main()
