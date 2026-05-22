#!/usr/bin/env python3
"""BiliRSS - Bilibili Audio RSS Server
Web management + Download daemon + RSS generator
"""

import os
import json
import hashlib
import subprocess
import threading
import time
import re
import tempfile
import urllib.request
import urllib.parse
from http.cookiejar import MozillaCookieJar
from datetime import datetime, timezone, timedelta
from pathlib import Path
from flask import Flask, render_template_string, request, redirect, url_for, jsonify, send_from_directory

BASE_DIR = Path('/opt/bili-rss')
AUDIO_DIR = BASE_DIR / 'audio'
META_DIR = BASE_DIR / 'meta'
RSS_DIR = BASE_DIR / 'rss'
COOKIE_DIR = BASE_DIR / 'cookies'
DB_FILE = BASE_DIR / 'db.json'
GLOBAL_COOKIE_FILE = BASE_DIR / 'global_cookie.txt'
DOWNLOAD_LOCK = threading.Lock()
DOWNLOAD_STATUS = {}

CST = timezone(timedelta(hours=8))

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False


# ========== Database ==========
def load_db():
    if DB_FILE.exists():
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'categories': [], 'tasks': []}

def save_db(db):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

def get_category(db, cat_id):
    for c in db['categories']:
        if c['id'] == cat_id:
            return c
    return None


# ========== Cookie Helpers ==========
def cookie_str_to_netscape_file(cookie_str, task_id):
    """Convert raw cookie string to Netscape cookies.txt format for yt-dlp --cookies"""
    COOKIE_DIR.mkdir(parents=True, exist_ok=True)
    cookie_file = COOKIE_DIR / f'{task_id}.txt'

    lines = ['# Netscape HTTP Cookie File', '# https://curl.se/docs/http-cookies.html', '# This file was generated automatically', '']
    for pair in cookie_str.split(';'):
        pair = pair.strip()
        if not pair or '=' not in pair:
            continue
        name, _, value = pair.partition('=')
        name = name.strip()
        value = value.strip()
        lines.append(f'.bilibili.com\tTRUE\t/\tTRUE\t0\t{name}\t{value}')
    lines.append('')

    with open(cookie_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return str(cookie_file)

def get_cookie_file(task_id, cookie_str):
    """Get cookie file path for yt-dlp --cookies, or None if no cookie"""
    if not cookie_str or not cookie_str.strip():
        return None
    return cookie_str_to_netscape_file(cookie_str, task_id)

def save_global_cookie(cookie_str):
    """Save a global cookie string for all downloads to use"""
    if not cookie_str or not cookie_str.strip():
        return
    cookie_str_to_netscape_file(cookie_str, 'global')

def get_global_cookie_file():
    """Get global cookie file path if it exists"""
    f = COOKIE_DIR / 'global.txt'
    if f.exists():
        return str(f)
    return None

def resolve_cookie_file(task_id, cookie_str):
    """Resolve cookie file: task-specific cookie > global cookie > None"""
    if cookie_str and cookie_str.strip():
        return get_cookie_file(task_id, cookie_str)
    return get_global_cookie_file()


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

def audio_file_exists(bv_id):
    """Check if audio file already exists for a given BV ID"""
    for ext in ['.mp3', '.m4a', '.opus', '.webm', '.ogg']:
        if (AUDIO_DIR / f'{bv_id}{ext}').exists():
            return True
    return False

def download_audio(task_id, urls, cat_id, cookie_str=None):
    db = load_db()
    DOWNLOAD_STATUS[task_id] = {'status': 'running', 'progress': 0, 'total': len(urls), 'message': 'Downloading...'}

    success_count = 0
    all_bv_ids = []
    cookie_file = resolve_cookie_file(task_id, cookie_str)
    for i, url in enumerate(urls):
        try:
            DOWNLOAD_STATUS[task_id]['progress'] = i
            DOWNLOAD_STATUS[task_id]['message'] = f'Downloading {i+1}/{len(urls)}: {url[:50]}'

            # Check if already downloaded
            bv_id = extract_bv_id(url)
            if bv_id and audio_file_exists(bv_id):
                success_count += 1
                all_bv_ids.append(bv_id)
                DOWNLOAD_STATUS[task_id]['message'] = f'Skipped (already exists): {bv_id}'
                continue

            cmd = [
                'yt-dlp',
                '-x', '--audio-format', 'mp3', '--audio-quality', '0',
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
                # Extract BV IDs from output
                for line in result.stdout.split('\n'):
                    m = re.search(r'(BV[a-zA-Z0-9]+)', line)
                    if m:
                        all_bv_ids.append(m.group(1))
            else:
                error_msg = result.stderr[-200:] if result.stderr else 'Unknown error'
                DOWNLOAD_STATUS[task_id]['message'] = f'Error: {error_msg}'
        except subprocess.TimeoutExpired:
            DOWNLOAD_STATUS[task_id]['message'] = f'Timeout on {url[:30]}'
        except Exception as e:
            DOWNLOAD_STATUS[task_id]['message'] = f'Exception: {str(e)[:80]}'

    # Update task bv_ids
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
        'message': f'Done! {success_count}/{len(urls)} succeeded'
    }

def fetch_up_video_list(uid, cookie_str):
    """Fetch all BV IDs from a UP main using Bilibili Polymer API"""
    bv_ids = []
    offset = ''
    page = 1

    # Try task-specific cookie first, then global cookie
    if not cookie_str or not cookie_str.strip():
        # Try to read global cookie
        global_cookie_path = COOKIE_DIR / 'global.txt'
        if not global_cookie_path.exists():
            # Check any existing cookie file
            cookie_files = list(COOKIE_DIR.glob('*.txt'))
            if cookie_files:
                # Use the most recent one
                latest = max(cookie_files, key=lambda f: f.stat().st_mtime)
                try:
                    # Read cookies from Netscape file and convert back to string
                    cookie_pairs = []
                    with open(latest, 'r') as f:
                        for line in f:
                            parts = line.strip().split('\t')
                            if len(parts) >= 7 and not parts[0].startswith('#'):
                                cookie_pairs.append(f'{parts[5]}={parts[6]}')
                    if cookie_pairs:
                        cookie_str = '; '.join(cookie_pairs)
                except:
                    pass

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
        except Exception as e:
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
        page += 1

        if not has_more or not offset:
            break

        # Rate limit: 1 request per second
        time.sleep(1)

    return bv_ids


def download_up_videos(task_id, uid, cat_id, cookie_str=None):
    """Download all videos from a UP main using Polymer API"""
    DOWNLOAD_STATUS[task_id] = {'status': 'running', 'progress': 0, 'total': 1, 'message': f'Fetching UP {uid} video list via Polymer API...'}

    try:
        bv_ids = fetch_up_video_list(uid, cookie_str)

        if not bv_ids:
            DOWNLOAD_STATUS[task_id] = {'status': 'failed', 'progress': 0, 'total': 1,
                                         'message': f'No videos found for UP {uid}. Cookie may be required.' }
            return

        DOWNLOAD_STATUS[task_id]['total'] = len(bv_ids)
        DOWNLOAD_STATUS[task_id]['message'] = f'Found {len(bv_ids)} videos, downloading...'

        # Filter out already-downloaded videos
        already_exist = [bv for bv in bv_ids if audio_file_exists(bv)]
        to_download = [bv for bv in bv_ids if not audio_file_exists(bv)]

        if already_exist:
            DOWNLOAD_STATUS[task_id]['message'] = f'Found {len(bv_ids)} videos ({len(already_exist)} already downloaded), downloading {len(to_download)} new...'

        # Still record all BV IDs
        db = load_db()
        for task in db['tasks']:
            if task['id'] == task_id:
                existing = set(task.get('bv_ids', []))
                task['bv_ids'] = list(existing | set(bv_ids))
                break
        save_db(db)

        # Download only new ones
        if to_download:
            urls = [f'https://www.bilibili.com/video/{bv}' for bv in to_download]
            download_audio(task_id, urls, cat_id, cookie_str)
            # Fix the total count in final status to include skipped ones
            if task_id in DOWNLOAD_STATUS:
                s = DOWNLOAD_STATUS[task_id]
                msg = s.get('message', '')
                try:
                    parts = msg.replace('Done! ', '').split('/')
                    succeeded_in_batch = int(parts[0]) if parts else 0
                except:
                    succeeded_in_batch = 0
                total_succeeded = succeeded_in_batch + len(already_exist)
                total_all = len(bv_ids)
                s['total'] = total_all
                s['progress'] = total_all
                s['message'] = f'Done! {total_succeeded}/{total_all} succeeded ({len(already_exist)} already existed)'
        else:
            # All already downloaded
            generate_rss()
            DOWNLOAD_STATUS[task_id] = {
                'status': 'completed',
                'progress': len(bv_ids),
                'total': len(bv_ids),
                'message': f'Done! {len(bv_ids)}/{len(bv_ids)} succeeded (all already existed)'
            }

    except Exception as e:
        DOWNLOAD_STATUS[task_id] = {'status': 'failed', 'progress': 0, 'total': 1,
                                     'message': f'Exception: {str(e)[:80]}'}


# ========== RSS Generation ==========
def generate_rss():
    db = load_db()
    base_url = 'http://服务器IP'

    # Per-category RSS
    for cat in db['categories']:
        cat_id = cat['id']
        items = []
        bv_ids_in_cat = set()
        for t in db['tasks']:
            if t.get('category_id') == cat_id:
                bv_ids_in_cat.update(t.get('bv_ids', []))

        for meta_file in sorted(AUDIO_DIR.glob('*.info.json'), key=lambda f: f.stat().st_mtime, reverse=True):
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                bv_id = info.get('id', meta_file.stem.replace('.info', ''))
                if bv_ids_in_cat and bv_id not in bv_ids_in_cat:
                    continue
                item = build_rss_item(info, bv_id, base_url)
                if item:
                    items.append(item)
            except Exception:
                continue

        rss_xml = build_rss_xml(cat['name'], cat.get('description', f'Bilibili audio - {cat["name"]}'), items, base_url)
        with open(RSS_DIR / f'{cat_id}.xml', 'w', encoding='utf-8') as f:
            f.write(rss_xml)

    # Global RSS
    all_items = []
    for meta_file in sorted(AUDIO_DIR.glob('*.info.json'), key=lambda f: f.stat().st_mtime, reverse=True):
        try:
            with open(meta_file, 'r', encoding='utf-8') as f:
                info = json.load(f)
            bv_id = info.get('id', meta_file.stem.replace('.info', ''))
            item = build_rss_item(info, bv_id, base_url)
            if item:
                all_items.append(item)
        except Exception:
            continue

    rss_xml = build_rss_xml('All Bilibili Audio', 'All downloaded Bilibili audio', all_items, base_url)
    with open(RSS_DIR / 'all.xml', 'w', encoding='utf-8') as f:
        f.write(rss_xml)

def build_rss_item(info, bv_id, base_url):
    audio_path = None
    for ext in ['.mp3', '.m4a', '.opus', '.webm', '.ogg']:
        p = AUDIO_DIR / f'{bv_id}{ext}'
        if p.exists():
            audio_path = p
            break
    if not audio_path:
        return None

    ext = audio_path.suffix.lstrip('.')
    mime_map = {'mp3': 'audio/mpeg', 'm4a': 'audio/mp4', 'opus': 'audio/opus', 'webm': 'audio/webm', 'ogg': 'audio/ogg'}
    thumb_url = ''
    thumb_file = AUDIO_DIR / f'{bv_id}.jpg'
    if thumb_file.exists():
        thumb_url = f'{base_url}/audio/{bv_id}.jpg'

    return {
        'title': info.get('title', bv_id),
        'bv_id': bv_id,
        'uploader': info.get('uploader', info.get('channel', 'Unknown')),
        'duration': int(info.get('duration', 0)),
        'description': str(info.get('description', ''))[:200],
        'upload_date': info.get('upload_date', ''),
        'audio_url': f'{base_url}/audio/{audio_path.name}',
        'mime': mime_map.get(ext, 'audio/mpeg'),
        'size': audio_path.stat().st_size,
        'thumbnail': thumb_url,
    }

def build_rss_xml(title, description, items, base_url):
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">')
    lines.append('  <channel>')
    lines.append(f'    <title>{escape_xml(title)}</title>')
    lines.append(f'    <description>{escape_xml(description)}</description>')
    lines.append(f'    <link>{base_url}</link>')
    lines.append(f'    <language>zh-cn</language>')
    lines.append(f'    <lastBuildDate>{datetime.now(CST).strftime("%a, %d %b %Y %H:%M:%S %z")}</lastBuildDate>')
    lines.append(f'    <itunes:category text="Music"/>')

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
def get_audio_list(cat_id=None):
    db = load_db()
    result = []
    for meta_file in sorted(AUDIO_DIR.glob('*.info.json'), key=lambda f: f.stat().st_mtime, reverse=True):
        try:
            with open(meta_file, 'r', encoding='utf-8') as f:
                info = json.load(f)
            bv_id = info.get('id', meta_file.stem.replace('.info', ''))

            if cat_id:
                bv_ids_in_cat = set()
                for t in db['tasks']:
                    if t.get('category_id') == cat_id:
                        bv_ids_in_cat.update(t.get('bv_ids', []))
                if bv_id not in bv_ids_in_cat:
                    continue

            audio_path = None
            for ext in ['.mp3', '.m4a', '.opus', '.webm', '.ogg']:
                p = AUDIO_DIR / f'{bv_id}{ext}'
                if p.exists():
                    audio_path = p
                    break
            if not audio_path:
                continue

            duration = int(info.get('duration', 0))
            mins, secs = divmod(duration, 60)
            size = audio_path.stat().st_size
            size_str = f'{size/1024/1024:.1f}MB' if size > 1024*1024 else f'{size/1024:.0f}KB'

            thumb_url = ''
            thumb_file = AUDIO_DIR / f'{bv_id}.jpg'
            if thumb_file.exists():
                thumb_url = f'/audio/{bv_id}.jpg'

            result.append({
                'bv_id': bv_id,
                'title': info.get('title', bv_id),
                'uploader': info.get('uploader', info.get('channel', 'Unknown')),
                'duration_str': f'{mins}:{secs:02d}',
                'size_str': size_str,
                'audio_url': f'/audio/{audio_path.name}',
                'thumbnail': thumb_url,
            })
        except Exception:
            continue
    return result


# Import templates
from templates_index import TEMPLATE_INDEX
from templates_category import CATEGORY_DETAIL_TEMPLATE


# ========== Web Routes ==========
@app.route('/')
def index():
    db = load_db()
    categories = []
    for cat in db['categories']:
        cat_audio = get_audio_list(cat['id'])
        cat['audio_count'] = len(cat_audio)
        categories.append(cat)

    tasks = []
    for task in db['tasks']:
        cat = get_category(db, task.get('category_id', ''))
        task['category_name'] = cat['name'] if cat else 'Unknown'
        task_id = task['id']
        if task_id in DOWNLOAD_STATUS:
            task['dl_status'] = DOWNLOAD_STATUS[task_id]['status']
        elif task.get('status'):
            task['dl_status'] = task['status']
        else:
            task['dl_status'] = 'pending'
        tasks.append(task)

    audio_list = get_audio_list()
    audio_count = len(audio_list)
    return render_template_string(TEMPLATE_INDEX, categories=categories, tasks=tasks, audio_list=audio_list, audio_count=audio_count)


@app.route('/category/<cat_id>')
def category_detail(cat_id):
    db = load_db()
    cat = get_category(db, cat_id)
    if not cat:
        return redirect('/')
    audio_list = get_audio_list(cat_id)
    return render_template_string(CATEGORY_DETAIL_TEMPLATE, category=cat, audio_list=audio_list)


# ========== API Routes ==========
@app.route('/api/category', methods=['POST'])
def api_create_category():
    db = load_db()
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    if not name:
        return jsonify({'ok': False, 'error': 'Name required'}), 400

    cat_id = hashlib.md5(name.encode()).hexdigest()[:8]
    if get_category(db, cat_id):
        return jsonify({'ok': False, 'error': 'Category already exists'}), 400

    db['categories'].append({'id': cat_id, 'name': name, 'description': description})
    save_db(db)
    return redirect('/')


@app.route('/api/category/<cat_id>', methods=['DELETE'])
def api_delete_category(cat_id):
    db = load_db()
    db['categories'] = [c for c in db['categories'] if c['id'] != cat_id]
    db['tasks'] = [t for t in db['tasks'] if t.get('category_id') != cat_id]
    save_db(db)
    generate_rss()
    return jsonify({'ok': True})


@app.route('/api/task', methods=['POST'])
def api_create_task():
    db = load_db()
    cat_id = request.form.get('category_id', '').strip()
    url_type = request.form.get('url_type', 'video').strip()
    url = request.form.get('url', '').strip()
    cookie = request.form.get('cookie', '').strip()

    if not url or not cat_id:
        return jsonify({'ok': False, 'error': 'URL and category required'}), 400

    cat = get_category(db, cat_id)
    if not cat:
        return jsonify({'ok': False, 'error': 'Category not found'}), 400

    task_id = hashlib.md5(f'{cat_id}:{url}:{time.time()}'.encode()).hexdigest()[:8]

    # Save cookie globally if provided
    if cookie:
        save_global_cookie(cookie)

    uid = ''
    if url_type == 'video':
        bv_id = extract_bv_id(url)
        if not bv_id:
            return jsonify({'ok': False, 'error': 'Invalid BV link'}), 400
        dl_url = f'https://www.bilibili.com/video/{bv_id}'
        task_name = f'Video: {bv_id}'
        bv_ids = [bv_id]
    elif url_type == 'up':
        uid = extract_uid(url)
        if not uid:
            return jsonify({'ok': False, 'error': 'Invalid UID'}), 400
        dl_url = f'https://space.bilibili.com/{uid}/video'
        task_name = f'UP: {uid}'
        bv_ids = []
    elif url_type == 'fav':
        dl_url = url if url.startswith('http') else f'https://space.bilibili.com/favlist?fid={url}'
        task_name = f'Favorites: {url[:20]}'
        bv_ids = []
    elif url_type == 'search':
        dl_url = f'bili360search:{url}'
        task_name = f'Search: {url[:20]}'
        bv_ids = []
    else:
        return jsonify({'ok': False, 'error': 'Invalid type'}), 400

    task = {
        'id': task_id,
        'category_id': cat_id,
        'name': task_name,
        'url_type': url_type,
        'url': dl_url,
        'uid': uid,
        'cookie': cookie,
        'bv_ids': bv_ids,
        'created_at': datetime.now(CST).isoformat(),
        'status': 'running',
    }
    db['tasks'].append(task)
    save_db(db)

    # Start download in background
    if url_type == 'up':
        t = threading.Thread(target=download_up_videos, args=(task_id, uid, cat_id, cookie))
    else:
        t = threading.Thread(target=download_audio, args=(task_id, [dl_url], cat_id, cookie))
    t.daemon = True
    t.start()

    return redirect('/')


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
        return jsonify({'ok': False, 'error': 'Task not found'}), 404

    task['status'] = 'running'
    save_db(db)

    if task.get('url_type') == 'up':
        uid = task.get('uid') or extract_uid(task['url']) or ''
        t = threading.Thread(target=download_up_videos, args=(task_id, uid, task.get('category_id'), task.get('cookie')))
    else:
        t = threading.Thread(target=download_audio, args=(task_id, [task['url']], task.get('category_id'), task.get('cookie')))
    t.daemon = True
    t.start()
    return jsonify({'ok': True})


@app.route('/api/audio/<bv_id>', methods=['DELETE'])
def api_delete_audio(bv_id):
    deleted = False
    for ext in ['.mp3', '.m4a', '.opus', '.webm', '.ogg', '.jpg', '.webp', '.png']:
        p = AUDIO_DIR / f'{bv_id}{ext}'
        if p.exists():
            p.unlink()
            deleted = True
    meta = META_DIR / f'{bv_id}.info.json'
    if meta.exists():
        meta.unlink()
        deleted = True
    # Also clean info.json from AUDIO_DIR
    meta2 = AUDIO_DIR / f'{bv_id}.info.json'
    if meta2.exists():
        meta2.unlink()
        deleted = True
    generate_rss()
    return jsonify({'ok': True, 'deleted': deleted})


@app.route('/api/rss/regenerate', methods=['POST'])
def api_regenerate_rss():
    generate_rss()
    return jsonify({'ok': True, 'message': 'RSS feeds regenerated!'})


@app.route('/api/status')
def api_status():
    return jsonify(DOWNLOAD_STATUS)


# ========== Static & RSS Routes ==========
@app.route('/audio/<path:filename>')
def serve_audio(filename):
    return send_from_directory(str(AUDIO_DIR), filename)


@app.route('/rss/<path:filename>')
def serve_rss(filename):
    return send_from_directory(str(RSS_DIR), filename, mimetype='application/xml')


if __name__ == '__main__':
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    META_DIR.mkdir(parents=True, exist_ok=True)
    RSS_DIR.mkdir(parents=True, exist_ok=True)

    with app.test_request_context():
        generate_rss()

    app.run(host='0.0.0.0', port=5000, debug=False)
