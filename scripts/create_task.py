#!/usr/bin/env python3
"""Create UP main task on the BiliRSS server"""
import urllib.request
import urllib.parse

with open('/tmp/bili_cookie.txt') as f:
    cookie = f.read().strip()

data = urllib.parse.urlencode({
    'category_id': 'c2956fa6',
    'url_type': 'up',
    'url': '3493127314737312',
    'cookie': cookie,
}).encode()

req = urllib.request.Request('http://localhost:5000/api/task', data=data)
with urllib.request.urlopen(req, timeout=10) as resp:
    print('Status:', resp.status)
    body = resp.read().decode()
    print('Body:', body[:200])
