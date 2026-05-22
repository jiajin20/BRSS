#!/usr/bin/env python3
"""Test Bilibili API to fetch UP's video list"""
import urllib.request
import json

cookie = open('/opt/bili-rss/test_cookie.txt').read().strip()
uid = '3493127314737312'

url = f'https://api.bilibili.com/x/space/wbi/arc/search?mid={uid}&ps=30&pn=1&order=pubdate'
req = urllib.request.Request(url)
req.add_header('Cookie', cookie)
req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36')
req.add_header('Referer', 'https://space.bilibili.com/')

try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
        print(f"Code: {data.get('code')}")
        print(f"Message: {data.get('message')}")
        if data.get('data') and data['data'].get('list') and data['data']['list'].get('vlist'):
            vlist = data['data']['list']['vlist']
            print(f"Total videos: {data['data']['page'].get('count', '?')}")
            for v in vlist[:5]:
                print(f"  BV: {v.get('bvid')} | {v.get('title')}")
        else:
            print('No video list found')
            print(f"Data keys: {list(data.get('data', {}).keys()) if data.get('data') else 'None'}")
except Exception as e:
    print(f"Error: {e}")
