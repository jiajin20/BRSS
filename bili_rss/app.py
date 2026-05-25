#!/usr/bin/env python3
"""BiliRSS - Bilibili Audio RSS Server
Web management + Download daemon + RSS generator
v5: Batch delete with secret key, dynamic stats API, improved UX
"""

import os
import json
import hashlib
import subprocess
import threading
import time
import re
import shutil
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from flask import Flask, render_template_string, request, redirect, url_for, jsonify, send_from_directory, has_request_context

BASE_DIR = Path('/opt/bili-rss')
AUDIO_DIR = BASE_DIR / 'audio'
META_DIR = BASE_DIR / 'meta'
RSS_DIR = BASE_DIR / 'rss'
COOKIE_DIR = BASE_DIR / 'cookies'
COVER_DIR = BASE_DIR / 'covers'
DB_FILE = BASE_DIR / 'db.json'
DOWNLOAD_STATUS = {}
db_lock = threading.Lock()  # 保护 db.json 的并发读写

# RSS 基础 URL，用于生成 enclosure 音频链接。
# 优先级：环境变量 BILI_RSS_BASE_URL > 代码中显式设置 > 本默认值
# 服务器端部署示例（Linux systemd）：
#   Environment="BILI_RSS_BASE_URL=http://47.108.188.75"
# run_local.py 会自动 patch 为 http://127.0.0.1:5000
import os as _os
BASE_URL = _os.environ.get('BILI_RSS_BASE_URL', 'http://服务器IP')
del _os

# 记录最近一次有请求上下文时的访问地址，供后台线程生成 RSS 时使用
_last_known_base_url = None

def get_base_url():
    """获取当前 base_url。
    有请求上下文时：用 Host 请求头拼出当前访问地址（自适应 IP / 域名 / 反代）
    无请求上下文时（后台线程）：用最近记录的访问地址，否则用 BASE_URL 常量
    """
    global _last_known_base_url
    if has_request_context():
        # 优先用 X-Forwarded-Host（反代场景），否则用 Host 头
        host = request.headers.get('X-Forwarded-Host') or request.host
        # 协议：优先 X-Forwarded-Proto，否则用请求的 scheme
        scheme = request.headers.get('X-Forwarded-Proto') or request.scheme
        url = f'{scheme}://{host}'.rstrip('/')
        _last_known_base_url = url
        return url
    return _last_known_base_url or BASE_URL

CST = timezone(timedelta(hours=8))
SERVICE_START_TIME = time.time()

# Delete secret key (SHA256 hash stored for verification)
DELETE_SECRET_KEY = 'Ah+$ZnbC-#I.<rzzdtXX$,l?*0SYXfu{7dtgEjR+<p9]hi$n,aSxhH5A]f]muGNO'
DELETE_SECRET_KEY_HASH = hashlib.sha256(DELETE_SECRET_KEY.encode()).hexdigest()

AUDIO_FORMATS = {
    'mp3': {'label': 'MP3（通用压缩）', 'cmd': ['--audio-format', 'mp3', '--audio-quality', '0'], 'ext': '.mp3', 'mime': 'audio/mpeg'},
    'flac': {'label': 'FLAC（无损）', 'cmd': ['--audio-format', 'flac', '--audio-quality', '0'], 'ext': '.flac', 'mime': 'audio/flac'},
    'm4a': {'label': 'AAC/M4A（苹果兼容）', 'cmd': ['--audio-format', 'm4a', '--audio-quality', '0'], 'ext': '.m4a', 'mime': 'audio/mp4'},
    'opus': {'label': 'Opus（高效压缩）', 'cmd': ['--audio-format', 'opus', '--audio-quality', '0'], 'ext': '.opus', 'mime': 'audio/opus'},
    'wav': {'label': 'WAV（原始无损）', 'cmd': ['--audio-format', 'wav', '--audio-quality', '0'], 'ext': '.wav', 'mime': 'audio/wav'},
    'best': {'label': '最佳质量（自动）', 'cmd': ['--audio-format', 'best', '--audio-quality', '0'], 'ext': '', 'mime': 'audio/mpeg'},
}

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False


# ========== Database ==========
def load_db():
    if DB_FILE.exists():
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'categories': [], 'collections': [], 'tasks': []}

def save_db(db):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def get_category(db, cat_id):
    for c in db['categories']:
        if c['id'] == cat_id:
            return c
    return None

def get_collection(db, col_id):
    for c in db['collections']:
        if c['id'] == col_id:
            return c
    return None


# ========== Server Status ==========
def get_server_status():
    """Get server disk usage, uptime, etc."""
    # Use shutil.disk_usage for cross-platform support (Linux + Windows)
    import shutil as _shutil
    disk_usage = _shutil.disk_usage(str(BASE_DIR))
    total_bytes = disk_usage.total
    used_bytes = disk_usage.used
    free_bytes = disk_usage.free

    def fmt_size(b):
        if b >= 1024**3:
            return f'{b/1024/1024/1024:.1f} GB'
        elif b >= 1024**2:
            return f'{b/1024/1024:.0f} MB'
        else:
            return f'{b/1024:.0f} KB'

    uptime_seconds = int(time.time() - SERVICE_START_TIME)
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    if days > 0:
        uptime_str = f'{days}天 {hours}小时 {minutes}分'
    elif hours > 0:
        uptime_str = f'{hours}小时 {minutes}分'
    else:
        uptime_str = f'{minutes}分 {seconds}秒'

    return {
        'disk_total': fmt_size(total_bytes),
        'disk_used': fmt_size(used_bytes),
        'disk_free': fmt_size(free_bytes),
        'disk_percent': round(used_bytes / total_bytes * 100, 1) if total_bytes > 0 else 0,
        'uptime': uptime_str,
        'uptime_seconds': uptime_seconds,
        'start_time': SERVICE_START_TIME,
    }


# ========== Cookie Helpers ==========
def get_client_ip():
    """获取客户端真实IP（支持反向代理）"""
    xff = request.headers.get('X-Forwarded-For', '')
    if xff:
        return xff.split(',')[0].strip()
    return request.remote_addr or '127.0.0.1'

def ip_cookie_key(ip):
    """IP → 固定 hash，同一IP共享cookie"""
    return hashlib.md5(f'bili_cookie_{ip}'.encode()).hexdigest()[:12]

def cookie_str_to_netscape_file(cookie_str, name):
    COOKIE_DIR.mkdir(parents=True, exist_ok=True)
    cookie_file = COOKIE_DIR / f'{name}.txt'
    lines = ['# Netscape HTTP Cookie File', '# https://curl.se/docs/http-cookies.html', '# This file was generated automatically', '']
    for pair in cookie_str.split(';'):
        pair = pair.strip()
        if not pair or '=' not in pair:
            continue
        name_part, _, value = pair.partition('=')
        name_part, value = name_part.strip(), value.strip()
        lines.append(f'.bilibili.com\tTRUE\t/\tTRUE\t0\t{name_part}\t{value}')
    lines.append('')
    with open(cookie_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return str(cookie_file)

def save_cookie_for_ip(cookie_str, ip):
    """保存IP对应的全局cookie"""
    if not cookie_str or not cookie_str.strip():
        return
    key = ip_cookie_key(ip)
    cookie_str_to_netscape_file(cookie_str, key)

def resolve_cookie_file(ip, cookie_str=None):
    """按IP查找cookie文件：IP专属 > 提供的新cookie > None"""
    key = ip_cookie_key(ip)
    f = COOKIE_DIR / f'{key}.txt'
    if f.exists():
        return str(f)
    if cookie_str and cookie_str.strip():
        return cookie_str_to_netscape_file(cookie_str, key)
    return None

def read_cookie_str_from_file(ip):
    """从IP专属cookie文件读取cookie字符串（用于B站API请求头）"""
    key = ip_cookie_key(ip)
    f = COOKIE_DIR / f'{key}.txt'
    if not f.exists():
        return ''
    try:
        pairs = []
        with open(f, 'r') as fh:
            for line in fh:
                parts = line.strip().split('\t')
                if len(parts) >= 7 and not parts[0].startswith('#'):
                    pairs.append(f'{parts[5]}={parts[6]}')
        return '; '.join(pairs)
    except:
        return ''


# ========== Download ==========
def extract_bv_id(url_or_id):
    url_or_id = url_or_id.strip()
    m = re.search(r'(BV[a-zA-Z0-9]+)', url_or_id)
    if m:
        return m.group(1)
    if url_or_id.startswith('BV') and len(url_or_id) >= 10:
        return url_or_id
    return None

def extract_uid(url_or_id):
    url_or_id = url_or_id.strip()
    for pattern in [r'space\.bilibili\.com/(\d+)', r'bilibili\.com/(\d+)']:
        m = re.search(pattern, url_or_id)
        if m:
            return m.group(1)
    if url_or_id.isdigit():
        return url_or_id
    return None

def get_audio_ext(bv_id, fmt='mp3'):
    """Get the actual audio file extension for a BV ID"""
    if fmt == 'best':
        for ext in ['.mp3', '.m4a', '.flac', '.opus', '.wav', '.ogg', '.webm']:
            if (AUDIO_DIR / f'{bv_id}{ext}').exists():
                return ext
        return '.mp3'
    target_ext = AUDIO_FORMATS.get(fmt, AUDIO_FORMATS['mp3'])['ext']
    if target_ext and (AUDIO_DIR / f'{bv_id}{target_ext}').exists():
        return target_ext
    # fallback: find any existing audio
    for ext in ['.mp3', '.m4a', '.flac', '.opus', '.wav', '.ogg', '.webm']:
        if (AUDIO_DIR / f'{bv_id}{ext}').exists():
            return ext
    return target_ext or '.mp3'

def audio_file_exists(bv_id):
    for ext in ['.mp3', '.m4a', '.flac', '.opus', '.wav', '.ogg', '.webm']:
        if (AUDIO_DIR / f'{bv_id}{ext}').exists():
            return True
    return False

def download_audio(task_id, urls, cat_id, ip, cookie_str=None, audio_format='mp3'):
    db = load_db()
    DOWNLOAD_STATUS[task_id] = {'status': 'running', 'progress': 0, 'total': len(urls), 'message': '下载中...'}

    success_count = 0
    all_bv_ids = []
    cookie_file = resolve_cookie_file(ip, cookie_str)
    fmt_info = AUDIO_FORMATS.get(audio_format, AUDIO_FORMATS['mp3'])

    for i, url in enumerate(urls):
        try:
            DOWNLOAD_STATUS[task_id]['progress'] = i
            DOWNLOAD_STATUS[task_id]['message'] = f'下载中 {i+1}/{len(urls)}: {url[:50]}'

            bv_id = extract_bv_id(url)
            if bv_id and audio_file_exists(bv_id):
                success_count += 1
                all_bv_ids.append(bv_id)
                DOWNLOAD_STATUS[task_id]['message'] = f'跳过（已存在）: {bv_id}'
                continue

            cmd = [
                'yt-dlp',
                '-x',
                *fmt_info['cmd'],
                '-o', str(AUDIO_DIR / '%(id)s.%(ext)s'),
                '--write-info-json',
                '--write-thumbnail',
                '--convert-thumbnails', 'jpg',
                '--no-check-certificates',
            ]
            if cookie_file:
                cmd.extend(['--cookies', cookie_file])
            cmd.append(url)

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

            if result.returncode == 0:
                success_count += 1
                for line in result.stdout.split('\n'):
                    m = re.search(r'(BV[a-zA-Z0-9]+)', line)
                    if m:
                        all_bv_ids.append(m.group(1))
            else:
                error_msg = result.stderr[-200:] if result.stderr else '未知错误'
                DOWNLOAD_STATUS[task_id]['message'] = f'错误: {error_msg}'
        except subprocess.TimeoutExpired:
            DOWNLOAD_STATUS[task_id]['message'] = f'超时: {url[:30]}'
        except Exception as e:
            DOWNLOAD_STATUS[task_id]['message'] = f'异常: {str(e)[:80]}'

    with db_lock:
        db = load_db()
        for task in db['tasks']:
            if task['id'] == task_id:
                existing = set(task.get('bv_ids', []))
                task['bv_ids'] = list(existing | set(all_bv_ids))
                task['status'] = 'completed'
                break
        save_db(db)

    generate_rss()
    DOWNLOAD_STATUS[task_id] = {
        'status': 'completed',
        'progress': len(urls),
        'total': len(urls),
        'message': f'完成！{success_count}/{len(urls)} 成功'
    }

def fetch_up_video_list(uid, ip, cookie_str=None):
    bv_ids = []
    offset = ''

    if not cookie_str or not cookie_str.strip():
        cookie_str = read_cookie_str_from_file(ip)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Referer': f'https://space.bilibili.com/{uid}/video',
        'Origin': 'https://space.bilibili.com',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
    }
    if cookie_str:
        headers['Cookie'] = cookie_str

    while True:
        url = f'https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid={uid}'
        if offset:
            url += f'&offset={offset}'
        req = urllib.request.Request(url)
        for k, v in headers.items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
        except:
            break

        if data.get('code') != 0:
            break

        items = data.get('data', {}).get('items', [])
        if not items:
            break

        for item in items:
            if not isinstance(item, dict):
                continue
            modules = item.get('modules') or {}
            module_dynamic = modules.get('module_dynamic') or {}
            major = module_dynamic.get('major') or {}
            if major:
                archive = major.get('archive') or {}
                bvid = archive.get('bvid', '')
                if bvid and bvid.startswith('BV'):
                    bv_ids.append(bvid)

        has_more = data.get('data', {}).get('has_more', False)
        offset = data.get('data', {}).get('offset', '')
        if not has_more or not offset:
            break
        time.sleep(1)

    return bv_ids


def download_up_videos(task_id, uid, cat_id, ip, cookie_str=None, audio_format='mp3'):
    DOWNLOAD_STATUS[task_id] = {'status': 'running', 'progress': 0, 'total': 1, 'message': f'正在获取 UP主 {uid} 的视频列表...'}

    try:
        bv_ids = fetch_up_video_list(uid, ip, cookie_str)
        if not bv_ids:
            DOWNLOAD_STATUS[task_id] = {'status': 'failed', 'progress': 0, 'total': 1,
                                         'message': f'未找到 UP主 {uid} 的视频，可能需要 Cookie'}
            return

        DOWNLOAD_STATUS[task_id]['total'] = len(bv_ids)
        DOWNLOAD_STATUS[task_id]['message'] = f'发现 {len(bv_ids)} 个视频，正在下载...'

        already_exist = [bv for bv in bv_ids if audio_file_exists(bv)]
        to_download = [bv for bv in bv_ids if not audio_file_exists(bv)]

        if already_exist:
            DOWNLOAD_STATUS[task_id]['message'] = f'发现 {len(bv_ids)} 个视频（{len(already_exist)} 个已下载），正在下载 {len(to_download)} 个新视频...'

        with db_lock:
            db = load_db()
            for task in db['tasks']:
                if task['id'] == task_id:
                    existing = set(task.get('bv_ids', []))
                    task['bv_ids'] = list(existing | set(bv_ids))
                    break
            save_db(db)

        if to_download:
            urls = [f'https://www.bilibili.com/video/{bv}' for bv in to_download]
            download_audio(task_id, urls, cat_id, ip, cookie_str, audio_format)
            if task_id in DOWNLOAD_STATUS:
                s = DOWNLOAD_STATUS[task_id]
                msg = s.get('message', '')
                try:
                    parts = msg.replace('完成！', '').split('/')
                    succeeded_in_batch = int(parts[0]) if parts else 0
                except:
                    succeeded_in_batch = 0
                total_succeeded = succeeded_in_batch + len(already_exist)
                total_all = len(bv_ids)
                s['total'] = total_all
                s['progress'] = total_all
                s['message'] = f'完成！{total_succeeded}/{total_all} 成功（{len(already_exist)} 个已存在）'
        else:
            generate_rss()
            DOWNLOAD_STATUS[task_id] = {
                'status': 'completed',
                'progress': len(bv_ids),
                'total': len(bv_ids),
                'message': f'完成！{len(bv_ids)}/{len(bv_ids)} 成功（全部已存在）'
            }
    except Exception as e:
        DOWNLOAD_STATUS[task_id] = {'status': 'failed', 'progress': 0, 'total': 1,
                                     'message': f'异常: {str(e)[:80]}'}


# ========== RSS Generation ==========
def generate_rss():
    """生成所有 RSS 文件。
    有请求上下文时自动使用当前访问地址（自适应 IP / 域名 / 反代）；
    后台线程调用时回退到最近记录的访问地址或 BASE_URL 常量。
    """
    db = load_db()
    base_url = get_base_url()
    RSS_DIR.mkdir(parents=True, exist_ok=True)  # 确保 RSS 目录存在，避免写文件时崩溃

    # Per-category RSS
    for cat in db['categories']:
        cat_id = cat['id']
        items = []
        bv_ids_in_cat = set()
        for t in db['tasks']:
            if t.get('category_id') == cat_id:
                bv_ids_in_cat.update(t.get('bv_ids', []))
        for bv_id in bv_ids_in_cat:
            item = build_rss_item_by_bv(bv_id, base_url)
            if item:
                items.append(item)
        items.sort(key=lambda x: x.get('upload_date', ''), reverse=True)
        rss_xml = build_rss_xml(cat['name'], cat.get('description', f'Bilibili 音频 - {cat["name"]}'), items, base_url)
        with open(RSS_DIR / f'{cat_id}.xml', 'w', encoding='utf-8') as f:
            f.write(rss_xml)

    # Per-collection RSS
    for col in db.get('collections', []):
        col_id = col['id']
        items = []
        for bv_id in col.get('bv_ids', []):
            item = build_rss_item_by_bv(bv_id, base_url)
            if item:
                items.append(item)
        items.sort(key=lambda x: x.get('upload_date', ''), reverse=True)
        col_cover = ''
        if col.get('cover'):
            col_cover = f'{base_url}/covers/{col["cover"]}'
        rss_xml = build_rss_xml(col['name'], col.get('description', f'合集 - {col["name"]}'), items, base_url, image_url=col_cover)
        with open(RSS_DIR / f'col_{col_id}.xml', 'w', encoding='utf-8') as f:
            f.write(rss_xml)

    # Global RSS
    all_items = []
    seen = set()
    for bv_id in get_all_bv_ids(db):
        if bv_id not in seen:
            item = build_rss_item_by_bv(bv_id, base_url)
            if item:
                all_items.append(item)
                seen.add(bv_id)
    all_items.sort(key=lambda x: x.get('upload_date', ''), reverse=True)
    rss_xml = build_rss_xml('全部 Bilibili 音频', '所有已下载的 Bilibili 音频', all_items, base_url)
    with open(RSS_DIR / 'all.xml', 'w', encoding='utf-8') as f:
        f.write(rss_xml)


def get_all_bv_ids(db):
    bv_ids = set()
    for t in db.get('tasks', []):
        bv_ids.update(t.get('bv_ids', []))
    for c in db.get('collections', []):
        bv_ids.update(c.get('bv_ids', []))
    return bv_ids


def build_rss_item_by_bv(bv_id, base_url):
    # Find info.json
    info_file = AUDIO_DIR / f'{bv_id}.info.json'
    if not info_file.exists():
        info_file_meta = META_DIR / f'{bv_id}.info.json'
        if info_file_meta.exists():
            info_file = info_file_meta
        else:
            return None
    try:
        with open(info_file, 'r', encoding='utf-8') as f:
            info = json.load(f)
    except:
        return None

    # Find audio file
    audio_path = None
    for ext in ['.mp3', '.m4a', '.flac', '.opus', '.wav', '.ogg', '.webm']:
        p = AUDIO_DIR / f'{bv_id}{ext}'
        if p.exists():
            audio_path = p
            break
    if not audio_path:
        return None

    ext = audio_path.suffix.lstrip('.')
    mime_map = {'mp3': 'audio/mpeg', 'm4a': 'audio/mp4', 'flac': 'audio/flac',
                'opus': 'audio/opus', 'wav': 'audio/wav', 'webm': 'audio/webm', 'ogg': 'audio/ogg'}
    thumb_url = ''
    if (AUDIO_DIR / f'{bv_id}.jpg').exists():
        thumb_url = f'{base_url}/audio/{bv_id}.jpg'

    return {
        'title': info.get('title', bv_id),
        'bv_id': bv_id,
        'uploader': info.get('uploader', info.get('channel', '未知')),
        'duration': int(info.get('duration', 0)),
        'description': str(info.get('description', ''))[:200],
        'upload_date': info.get('upload_date', ''),
        'audio_url': f'{base_url}/audio/{audio_path.name}',
        'mime': mime_map.get(ext, 'audio/mpeg'),
        'size': audio_path.stat().st_size,
        'thumbnail': thumb_url,
    }


def build_rss_xml(title, description, items, base_url, image_url=''):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">')
    lines.append('  <channel>')
    lines.append(f'    <title>{escape_xml(title)}</title>')
    lines.append(f'    <description>{escape_xml(description)}</description>')
    lines.append(f'    <link>{base_url}</link>')
    lines.append(f'    <language>zh-cn</language>')
    lines.append(f'    <lastBuildDate>{datetime.now(CST).strftime("%a, %d %b %Y %H:%M:%S %z")}</lastBuildDate>')
    lines.append(f'    <itunes:category text="Music"/>')
    if image_url:
        lines.append(f'    <itunes:image href="{escape_xml(image_url)}"/>')
        lines.append(f'    <image>')
        lines.append(f'      <url>{escape_xml(image_url)}</url>')
        lines.append(f'      <title>{escape_xml(title)}</title>')
        lines.append(f'      <link>{base_url}</link>')
        lines.append(f'    </image>')

    for item in items:
        lines.append('    <item>')
        lines.append(f'      <title>{escape_xml(item["title"])}</title>')
        lines.append(f'      <description>{escape_xml(item["description"])}</description>')
        if item.get("upload_date"):
            try:
                dt = datetime.strptime(item["upload_date"], "%Y%m%d")
                lines.append(f'      <pubDate>{dt.strftime("%a, %d %b %Y 00:00:00 +0800")}</pubDate>')
            except:
                pass
        lines.append(f'      <enclosure url="{escape_xml(item["audio_url"])}" type="{item["mime"]}" length="{item["size"]}"/>')
        if item.get("thumbnail"):
            lines.append(f'      <itunes:image href="{escape_xml(item["thumbnail"])}"/>')
        dur = int(item.get("duration", 0))
        if dur > 0:
            lines.append(f'      <itunes:duration>{dur}</itunes:duration>')
        lines.append(f'      <itunes:author>{escape_xml(item.get("uploader", ""))}</itunes:author>')
        lines.append('    </item>')

    lines.append('  </channel>')
    lines.append('</rss>')
    return '\n'.join(lines)

def escape_xml(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


# ========== Helpers ==========
def get_audio_info(bv_id):
    """Get audio file info for a BV ID"""
    info_file = AUDIO_DIR / f'{bv_id}.info.json'
    if not info_file.exists():
        info_file = META_DIR / f'{bv_id}.info.json'
    info = {}
    if info_file.exists():
        try:
            with open(info_file, 'r', encoding='utf-8') as f:
                info = json.load(f)
        except:
            pass

    audio_path = None
    for ext in ['.mp3', '.m4a', '.flac', '.opus', '.wav', '.ogg', '.webm']:
        p = AUDIO_DIR / f'{bv_id}{ext}'
        if p.exists():
            audio_path = p
            break

    if not audio_path:
        return None

    duration = int(info.get('duration', 0))
    mins, secs = divmod(duration, 60)
    size = audio_path.stat().st_size
    size_str = f'{size/1024/1024:.1f}MB' if size > 1024*1024 else f'{size/1024:.0f}KB'
    ext = audio_path.suffix.lstrip('.')

    thumb_url = ''
    if (AUDIO_DIR / f'{bv_id}.jpg').exists():
        thumb_url = f'/audio/{bv_id}.jpg'

    return {
        'bv_id': bv_id,
        'title': info.get('title', bv_id),
        'uploader': info.get('uploader', info.get('channel', '未知')),
        'duration': duration,
        'duration_str': f'{mins}:{secs:02d}' if duration > 0 else '--:--',
        'size': size,
        'size_str': size_str,
        'format': ext.upper(),
        'audio_url': f'/audio/{audio_path.name}',
        'thumbnail': thumb_url,
        'upload_date': info.get('upload_date', ''),
        'description': str(info.get('description', ''))[:100],
    }


def get_all_audio_list():
    """Get info for all downloaded audio files"""
    result = []
    seen = set()
    # Scan AUDIO_DIR for info.json files
    for info_file in AUDIO_DIR.glob('*.info.json'):
        bv_id = info_file.stem.replace('.info', '')
        if bv_id in seen:
            continue
        info = get_audio_info(bv_id)
        if info:
            result.append(info)
            seen.add(bv_id)
    # Also scan META_DIR
    for info_file in META_DIR.glob('*.info.json'):
        bv_id = info_file.stem.replace('.info', '')
        if bv_id in seen:
            continue
        info = get_audio_info(bv_id)
        if info:
            result.append(info)
            seen.add(bv_id)
    result.sort(key=lambda x: x.get('upload_date', ''), reverse=True)
    return result


# Import templates (relative import for local package; deploy.py flattens for server)
from .templates.index import TEMPLATE_INDEX
from .templates.category import CATEGORY_DETAIL_TEMPLATE


# ========== Web Routes ==========
@app.route('/')
def index():
    db = load_db()
    audio_list = get_all_audio_list()

    # Stats
    total_audio = len(audio_list)
    total_size = sum(a['size'] for a in audio_list)
    total_size_str = f'{total_size/1024/1024/1024:.1f}GB' if total_size > 1024**3 else f'{total_size/1024/1024:.0f}MB'

    categories = db.get('categories', [])
    for cat in categories:
        cat['audio_count'] = len([bv for t in db['tasks'] if t.get('category_id') == cat['id'] for bv in t.get('bv_ids', [])])

    collections = db.get('collections', [])
    for col in collections:
        col['audio_count'] = len(col.get('bv_ids', []))

    tasks = db.get('tasks', [])
    for task in tasks:
        cat = get_category(db, task.get('category_id', ''))
        task['category_name'] = cat['name'] if cat else '未知'
        task_id = task['id']
        if task_id in DOWNLOAD_STATUS:
            task['dl_status'] = DOWNLOAD_STATUS[task_id]['status']
            task['dl_message'] = DOWNLOAD_STATUS[task_id].get('message', '')
        elif task.get('status'):
            task['dl_status'] = task['status']
            task['dl_message'] = ''
        else:
            task['dl_status'] = 'pending'
            task['dl_message'] = ''

    # Format options for frontend
    format_options = {k: v['label'] for k, v in AUDIO_FORMATS.items()}

    # Server status
    server_status = get_server_status()

    return render_template_string(TEMPLATE_INDEX,
        categories=categories, collections=collections, tasks=tasks,
        audio_list=audio_list, total_audio=total_audio, total_size_str=total_size_str,
        format_options=format_options, server_status=server_status,
        total_collections=len(collections))


@app.route('/category/<cat_id>')
def category_detail(cat_id):
    db = load_db()
    cat = get_category(db, cat_id)
    if not cat:
        return redirect('/')
    bv_ids = set()
    for t in db['tasks']:
        if t.get('category_id') == cat_id:
            bv_ids.update(t.get('bv_ids', []))
    audio_list = [get_audio_info(bv) for bv in bv_ids]
    audio_list = [a for a in audio_list if a]
    audio_list.sort(key=lambda x: x.get('upload_date', ''), reverse=True)
    return render_template_string(CATEGORY_DETAIL_TEMPLATE, category=cat, audio_list=audio_list)


# ========== API Routes ==========
@app.route('/api/category', methods=['POST'])
def api_create_category():
    db = load_db()
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    if not name:
        return jsonify({'ok': False, 'error': '分类名称不能为空'}), 400
    cat_id = hashlib.md5(name.encode()).hexdigest()[:8]
    if get_category(db, cat_id):
        return jsonify({'ok': False, 'error': '分类已存在'}), 400
    db['categories'].append({'id': cat_id, 'name': name, 'description': description})
    save_db(db)
    return jsonify({'ok': True})

@app.route('/api/category/<cat_id>', methods=['DELETE'])
def api_delete_category(cat_id):
    db = load_db()
    db['categories'] = [c for c in db['categories'] if c['id'] != cat_id]
    db['tasks'] = [t for t in db['tasks'] if t.get('category_id') != cat_id]
    save_db(db)
    generate_rss()
    return jsonify({'ok': True})


# ---- Collections API ----
@app.route('/api/collection', methods=['POST'])
def api_create_collection():
    db = load_db()
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    delete_password = request.form.get('delete_password', '').strip()
    if not name:
        return jsonify({'ok': False, 'error': '合集名称不能为空'}), 400
    col_id = hashlib.md5(f'col:{name}:{time.time()}'.encode()).hexdigest()[:8]
    if 'collections' not in db:
        db['collections'] = []
    col_data = {
        'id': col_id,
        'name': name,
        'description': description,
        'bv_ids': [],
        'delete_password': '',
        'cover': '',
    }
    # Hash the delete password if provided
    if delete_password:
        col_data['delete_password'] = hashlib.sha256(delete_password.encode()).hexdigest()
    db['collections'].append(col_data)
    save_db(db)
    generate_rss()
    return jsonify({'ok': True, 'id': col_id})

@app.route('/api/collection/<col_id>', methods=['DELETE'])
def api_delete_collection(col_id):
    db = load_db()
    col = get_collection(db, col_id)
    if not col:
        return jsonify({'ok': False, 'error': '合集不存在'}), 404
    # Check password if set
    if col.get('delete_password'):
        provided_password = request.form.get('password', '').strip()
        if not provided_password:
            return jsonify({'ok': False, 'error': '此合集设有删除密码，请输入密码', 'need_password': True}), 403
        hashed = hashlib.sha256(provided_password.encode()).hexdigest()
        if hashed != col['delete_password']:
            return jsonify({'ok': False, 'error': '密码错误', 'need_password': True}), 403
    db['collections'] = [c for c in db.get('collections', []) if c['id'] != col_id]
    # Delete cover file if exists
    if col.get('cover'):
        cover_path = COVER_DIR / col['cover']
        if cover_path.exists():
            cover_path.unlink()
    save_db(db)
    generate_rss()
    return jsonify({'ok': True})

@app.route('/api/collection/<col_id>/check-password', methods=['POST'])
def api_check_collection_password(col_id):
    """Check if collection requires a password and verify it"""
    db = load_db()
    col = get_collection(db, col_id)
    if not col:
        return jsonify({'ok': False, 'error': '合集不存在'}), 404
    if not col.get('delete_password'):
        return jsonify({'ok': True, 'need_password': False})
    provided_password = request.form.get('password', '').strip()
    if not provided_password:
        return jsonify({'ok': False, 'need_password': True, 'error': '请输入密码'}), 403
    hashed = hashlib.sha256(provided_password.encode()).hexdigest()
    if hashed != col['delete_password']:
        return jsonify({'ok': False, 'need_password': True, 'error': '密码错误'}), 403
    return jsonify({'ok': True, 'need_password': True})

@app.route('/api/collection/<col_id>/add', methods=['POST'])
def api_collection_add(col_id):
    db = load_db()
    bv_ids = request.form.get('bv_ids', '').strip().split(',')
    bv_ids = [b.strip() for b in bv_ids if b.strip()]
    col = get_collection(db, col_id)
    if not col:
        return jsonify({'ok': False, 'error': '合集不存在'}), 404
    existing = set(col.get('bv_ids', []))
    col['bv_ids'] = list(existing | set(bv_ids))
    save_db(db)
    generate_rss()
    return jsonify({'ok': True, 'count': len(col['bv_ids'])})

@app.route('/api/collection/<col_id>/remove', methods=['POST'])
def api_collection_remove(col_id):
    db = load_db()
    bv_ids = request.form.get('bv_ids', '').strip().split(',')
    bv_ids = [b.strip() for b in bv_ids if b.strip()]
    col = get_collection(db, col_id)
    if not col:
        return jsonify({'ok': False, 'error': '合集不存在'}), 404
    existing = set(col.get('bv_ids', []))
    col['bv_ids'] = list(existing - set(bv_ids))
    save_db(db)
    generate_rss()
    return jsonify({'ok': True, 'count': len(col['bv_ids'])})

@app.route('/api/collection/<col_id>/cover', methods=['POST'])
def api_collection_cover(col_id):
    """Upload cover image for a collection"""
    db = load_db()
    col = get_collection(db, col_id)
    if not col:
        return jsonify({'ok': False, 'error': '合集不存在'}), 404

    if 'cover' not in request.files:
        return jsonify({'ok': False, 'error': '请选择封面图片'}), 400

    file = request.files['cover']
    if not file.filename:
        return jsonify({'ok': False, 'error': '请选择封面图片'}), 400

    # Validate file type
    allowed_exts = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_exts:
        return jsonify({'ok': False, 'error': '仅支持 JPG/PNG/GIF/WEBP 格式'}), 400

    # Save cover
    COVER_DIR.mkdir(parents=True, exist_ok=True)
    # Delete old cover if exists
    if col.get('cover'):
        old_cover = COVER_DIR / col['cover']
        if old_cover.exists():
            old_cover.unlink()

    cover_filename = f'{col_id}{ext}'
    file.save(str(COVER_DIR / cover_filename))
    col['cover'] = cover_filename
    save_db(db)
    generate_rss()
    return jsonify({'ok': True, 'cover_url': f'/covers/{cover_filename}'})


# ---- Task API ----
@app.route('/api/task', methods=['POST'])
def api_create_task():
    db = load_db()
    cat_id = request.form.get('category_id', '').strip()
    url_type = request.form.get('url_type', 'video').strip()
    url = request.form.get('url', '').strip()
    cookie = request.form.get('cookie', '').strip()
    audio_format = request.form.get('audio_format', 'mp3').strip()

    if not url or not cat_id:
        return jsonify({'ok': False, 'error': '请填写链接和选择分类'}), 400

    cat = get_category(db, cat_id)
    if not cat:
        return jsonify({'ok': False, 'error': '分类不存在'}), 400

    client_ip = get_client_ip()
    if cookie:
        save_cookie_for_ip(cookie, client_ip)

    task_id = hashlib.md5(f'{cat_id}:{url}:{time.time()}'.encode()).hexdigest()[:8]
    uid = ''

    if url_type == 'video':
        bv_id = extract_bv_id(url)
        if not bv_id:
            return jsonify({'ok': False, 'error': '无效的 BV 链接'}), 400
        dl_url = f'https://www.bilibili.com/video/{bv_id}'
        task_name = f'视频: {bv_id}'
        bv_ids = [bv_id]
    elif url_type == 'up':
        uid = extract_uid(url)
        if not uid:
            return jsonify({'ok': False, 'error': '无效的 UID'}), 400
        dl_url = f'https://space.bilibili.com/{uid}/video'
        task_name = f'UP主: {uid}'
        bv_ids = []
    else:
        return jsonify({'ok': False, 'error': '不支持的类型'}), 400

    task = {
        'id': task_id,
        'category_id': cat_id,
        'name': task_name,
        'url_type': url_type,
        'url': dl_url,
        'uid': uid,
        'ip_key': ip_cookie_key(client_ip),
        'cookie': cookie,
        'audio_format': audio_format,
        'bv_ids': bv_ids,
        'created_at': datetime.now(CST).isoformat(),
        'status': 'running',
    }
    db['tasks'].append(task)
    save_db(db)

    if url_type == 'up':
        t = threading.Thread(target=download_up_videos, args=(task_id, uid, cat_id, client_ip, cookie, audio_format))
    else:
        t = threading.Thread(target=download_audio, args=(task_id, [dl_url], cat_id, client_ip, cookie, audio_format))
    t.daemon = True
    t.start()

    return jsonify({'ok': True, 'task_id': task_id})

@app.route('/api/task/<task_id>', methods=['DELETE'])
def api_delete_task(task_id):
    db = load_db()
    db['tasks'] = [t for t in db['tasks'] if t['id'] != task_id]
    save_db(db)
    return jsonify({'ok': True})

@app.route('/api/task/<task_id>/download', methods=['POST'])
def api_redownload(task_id):
    db = load_db()
    task = None
    for t in db['tasks']:
        if t['id'] == task_id:
            task = t
            break
    if not task:
        return jsonify({'ok': False, 'error': '任务不存在'}), 404

    task['status'] = 'running'
    save_db(db)
    audio_format = task.get('audio_format', 'mp3')
    client_ip = get_client_ip()

    if task.get('url_type') == 'up':
        uid = task.get('uid') or extract_uid(task['url']) or ''
        t = threading.Thread(target=download_up_videos, args=(task_id, uid, task.get('category_id'), client_ip, task.get('cookie'), audio_format))
    else:
        t = threading.Thread(target=download_audio, args=(task_id, [task['url']], task.get('category_id'), client_ip, task.get('cookie'), audio_format))
    t.daemon = True
    t.start()
    return jsonify({'ok': True})


# ---- Audio API ----
@app.route('/api/audio/<bv_id>', methods=['DELETE'])
def api_delete_audio(bv_id):
    # Verify delete secret key
    secret_key = request.form.get('secret_key', '').strip()
    if not secret_key:
        return jsonify({'ok': False, 'error': '请输入删除密钥', 'need_key': True}), 403
    if hashlib.sha256(secret_key.encode()).hexdigest() != DELETE_SECRET_KEY_HASH:
        return jsonify({'ok': False, 'error': '密钥错误'}), 403

    deleted = False
    for ext in ['.mp3', '.m4a', '.flac', '.opus', '.wav', '.ogg', '.webm', '.jpg', '.webp', '.png', '.info.json']:
        p = AUDIO_DIR / f'{bv_id}{ext}'
        if p.exists():
            p.unlink()
            deleted = True
    meta = META_DIR / f'{bv_id}.info.json'
    if meta.exists():
        meta.unlink()
        deleted = True
    # Remove from all collections
    db = load_db()
    for col in db.get('collections', []):
        if bv_id in col.get('bv_ids', []):
            col['bv_ids'].remove(bv_id)
    save_db(db)
    generate_rss()
    return jsonify({'ok': True, 'deleted': deleted})


@app.route('/api/audio/batch-delete', methods=['POST'])
def api_batch_delete_audio():
    """Batch delete audio files with secret key verification"""
    secret_key = request.form.get('secret_key', '').strip()
    if not secret_key:
        return jsonify({'ok': False, 'error': '请输入删除密钥', 'need_key': True}), 403
    if hashlib.sha256(secret_key.encode()).hexdigest() != DELETE_SECRET_KEY_HASH:
        return jsonify({'ok': False, 'error': '密钥错误'}), 403

    bv_ids = request.form.get('bv_ids', '').strip().split(',')
    bv_ids = [b.strip() for b in bv_ids if b.strip()]
    if not bv_ids:
        return jsonify({'ok': False, 'error': '未选择要删除的文件'}), 400

    deleted_count = 0
    for bv_id in bv_ids:
        file_deleted = False
        for ext in ['.mp3', '.m4a', '.flac', '.opus', '.wav', '.ogg', '.webm', '.jpg', '.webp', '.png', '.info.json']:
            p = AUDIO_DIR / f'{bv_id}{ext}'
            if p.exists():
                p.unlink()
                file_deleted = True
        meta = META_DIR / f'{bv_id}.info.json'
        if meta.exists():
            meta.unlink()
            file_deleted = True
        if file_deleted:
            deleted_count += 1

    # Remove from all collections
    db = load_db()
    bv_id_set = set(bv_ids)
    for col in db.get('collections', []):
        col['bv_ids'] = [bv for bv in col.get('bv_ids', []) if bv not in bv_id_set]
    save_db(db)
    generate_rss()
    return jsonify({'ok': True, 'deleted': deleted_count})


@app.route('/api/audio/verify-key', methods=['POST'])
def api_verify_delete_key():
    """Verify delete secret key without performing any action"""
    secret_key = request.form.get('secret_key', '').strip()
    if not secret_key:
        return jsonify({'ok': False, 'error': '请输入密钥'}), 403
    if hashlib.sha256(secret_key.encode()).hexdigest() != DELETE_SECRET_KEY_HASH:
        return jsonify({'ok': False, 'error': '密钥错误'}), 403
    return jsonify({'ok': True})


@app.route('/api/audio/list', methods=['GET'])
def api_audio_list():
    search = request.args.get('search', '').strip().lower()
    audio_list = get_all_audio_list()
    if search:
        audio_list = [a for a in audio_list if search in a['title'].lower() or search in a['bv_id'].lower() or search in a.get('uploader', '').lower()]
    return jsonify(audio_list)


# ---- Stats API ----
@app.route('/api/stats')
def api_stats():
    """Dynamic stats for frontend polling"""
    db = load_db()
    audio_list = get_all_audio_list()
    total_audio = len(audio_list)
    total_size = sum(a['size'] for a in audio_list)
    total_size_str = f'{total_size/1024/1024/1024:.1f}GB' if total_size > 1024**3 else f'{total_size/1024/1024:.0f}MB'

    status = get_server_status()
    status['total_audio'] = total_audio
    status['total_size_str'] = total_size_str
    status['total_collections'] = len(db.get('collections', []))
    status['total_categories'] = len(db.get('categories', []))
    return jsonify(status)


# ---- RSS API ----
@app.route('/api/rss/regenerate', methods=['POST'])
def api_regenerate_rss():
    generate_rss()
    return jsonify({'ok': True, 'message': 'RSS 已重新生成！'})


# ---- Status API ----
@app.route('/api/status')
def api_status():
    return jsonify(DOWNLOAD_STATUS)

# ---- Server Status API ----
@app.route('/api/server-status')
def api_server_status():
    return jsonify(get_server_status())


# ========== Static & RSS Routes ==========
@app.route('/audio/<path:filename>')
def serve_audio(filename):
    return send_from_directory(str(AUDIO_DIR), filename)

@app.route('/rss/<path:filename>')
def serve_rss(filename):
    return send_from_directory(str(RSS_DIR), filename, mimetype='application/xml')

@app.route('/covers/<path:filename>')
def serve_cover(filename):
    return send_from_directory(str(COVER_DIR), filename)


if __name__ == '__main__':
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    META_DIR.mkdir(parents=True, exist_ok=True)
    RSS_DIR.mkdir(parents=True, exist_ok=True)
    COVER_DIR.mkdir(parents=True, exist_ok=True)
    COOKIE_DIR.mkdir(parents=True, exist_ok=True)

    with app.test_request_context():
        generate_rss()

    app.run(host='0.0.0.0', port=5000, debug=False)
