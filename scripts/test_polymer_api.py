#!/usr/bin/env python3
"""Test Polymer API to get UP's video list"""
import urllib.request
import json

cookie = open('/opt/bili-rss/test_cookie.txt').read().strip()
uid = '3493127314737312'

headers = {
    'Cookie': cookie,
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

# Fetch first page
url = f'https://api.bilibili.com/x/polymer/web-dynamic/v1/feed/space?host_mid={uid}&offset='
req = urllib.request.Request(url)
for k, v in headers.items():
    req.add_header(k, v)
with urllib.request.urlopen(req, timeout=10) as resp:
    data = json.loads(resp.read().decode())

items = data.get('data', {}).get('items', [])
total = data.get('data', {}).get('total', 0)
has_more = data.get('data', {}).get('has_more', False)
offset = data.get('data', {}).get('offset', '')

print(f"Total: {total}, Has more: {has_more}, Offset: {offset}")
print(f"Items count: {len(items)}")
print()

bv_ids = []
for item in items:
    # Each item is a dynamic card
    card_type = item.get('type', '')
    modules = item.get('modules', {})

    # Try to get video info from the dynamic
    major = modules.get('module_dynamic', {}).get('major', {})
    if major:
        archive = major.get('archive', {})
        if archive:
            bv = archive.get('aid', '')
            bvid = archive.get('bvid', '')
            title = archive.get('title', '')
            print(f"  Type: {card_type} | BV: {bvid} | AID: {bv} | {title}")
            if bvid:
                bv_ids.append(bvid)
            continue

    # Try author module for debug
    author = modules.get('module_author', {})
    name = author.get('name', '')
    desc = modules.get('module_dynamic', {}).get('desc', {}).get('text', '')[:50] if modules.get('module_dynamic', {}).get('desc') else ''

    print(f"  Type: {card_type} | Author: {name} | Desc: {desc}")

print(f"\nBV IDs found: {len(bv_ids)}")
print(f"BV list: {bv_ids}")

# Also check archive_count from user card
url2 = f'https://api.bilibili.com/x/web-interface/card?mid={uid}'
req2 = urllib.request.Request(url2)
for k, v in headers.items():
    req2.add_header(k, v)
with urllib.request.urlopen(req2, timeout=10) as resp:
    card_data = json.loads(resp.read().decode())
archive_count = card_data.get('data', {}).get('archive_count', 0)
print(f"\nArchive count from card: {archive_count}")
