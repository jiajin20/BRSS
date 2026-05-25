#!/usr/bin/env python3
"""
PyInstaller 打包脚本 — 将 deploy.py 打包为无 Python 依赖的 exe

用法:
    pip install pyinstaller
    python deploy/build_exe.py

输出:
    deploy/dist/BiliRSS-Deploy.exe    ← 可执行文件
    deploy/dist/config.ini            ← 配置文件（从 deploy/ 复制）
"""

import os
import sys
import shutil
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent          # deploy/
DIST_DIR = SCRIPT_DIR / 'dist'
DEPLOY_PY = SCRIPT_DIR / 'deploy.py'
CONFIG_INI = SCRIPT_DIR / 'config.ini'


def check_pyinstaller():
    try:
        import PyInstaller
        return True
    except ImportError:
        return False


def cleanup_old():
    """清理旧的构建产物"""
    dist_build = DIST_DIR / 'build'
    if dist_build.exists():
        shutil.rmtree(dist_build, ignore_errors=True)
    for p in DIST_DIR.glob('*.spec'):
        p.unlink()
    for p in SCRIPT_DIR.glob('*.spec'):
        p.unlink()


def create_default_ini():
    """创建默认 config.ini"""
    if not CONFIG_INI.exists():
        content = '''[BiliRSS Deploy]
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
        CONFIG_INI.write_text(content, encoding='utf-8')
        print('✅ 已创建默认 deploy/config.ini')


def main():
    print('═' * 50)
    print('  BiliRSS Deploy Exe 打包工具')
    print('═' * 50)

    if not check_pyinstaller():
        print('\n❌ 未安装 PyInstaller，请先运行:')
        print('   pip install pyinstaller')
        sys.exit(1)

    # 确保有 config.ini
    create_default_ini()

    print(f'\n📁 源文件: {DEPLOY_PY}')
    print(f'📁 输出目录: {DIST_DIR}')

    cleanup_old()
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    # 复制 config.ini 到 dist/（用户可直接编辑，与 exe 同目录）
    dist_ini = DIST_DIR / 'config.ini'
    shutil.copy2(CONFIG_INI, dist_ini)
    print(f'✅ config.ini 已复制到: {dist_ini}')

    # PyInstaller 打包
    print('\n🔨 正在打包 …')
    import PyInstaller.__main__

    args = [
        str(DEPLOY_PY),
        '--onefile',
        '--name', 'BiliRSS-Deploy',
        '--distpath', str(DIST_DIR),
        '--workpath', str(DIST_DIR / 'build'),
        '--specpath', str(DIST_DIR),
        '--console',
        '--clean',
        '--noconfirm',
        # 排除不需要的大模块以减小 exe 体积
        '--exclude-module', 'tkinter',
        '--exclude-module', 'matplotlib',
        '--exclude-module', 'numpy',
        '--exclude-module', 'pandas',
        '--exclude-module', 'PIL',
        '--exclude-module', 'cv2',
    ]

    PyInstaller.__main__.run(args)

    # 清理
    for sp in DIST_DIR.glob('*.spec'):
        sp.unlink()
    build_dir = DIST_DIR / 'build'
    if build_dir.exists():
        shutil.rmtree(build_dir, ignore_errors=True)

    exe_file = DIST_DIR / 'BiliRSS-Deploy.exe'
    if exe_file.exists():
        size_mb = exe_file.stat().st_size / (1024 * 1024)
        print(f'\n✅ 打包完成！')
        print(f'   {exe_file}')
        print(f'   文件大小: {size_mb:.1f} MB')
        print(f'\n📋 使用说明:')
        print(f'   1. 将 deploy/dist/ 整个文件夹拷贝到目标电脑')
        print(f'   2. 编辑 config.ini 填写服务器信息')
        print(f'   3. 双击 BiliRSS-Deploy.exe 运行')
    else:
        print('\n❌ 打包失败，exe 未生成')


if __name__ == '__main__':
    main()
