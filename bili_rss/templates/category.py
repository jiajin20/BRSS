#!/usr/bin/env python3
"""Category detail page template for BiliRSS"""

CATEGORY_DETAIL_TEMPLATE = r'''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ category.name }} - BiliRSS</title>
<style>
:root {
  --bg: #0f1117; --bg2: #1a1b26; --bg3: #24253a; --card: #1e1f31; --border: #2e3047;
  --text: #c0caf5; --text2: #a9b1d6; --text3: #787c99;
  --accent: #7aa2f7; --accent2: #bb9af7; --red: #f7768e; --green: #9ece6a; --yellow: #e0af68; --cyan: #7dcfff;
}
* { margin:0; padding:0; box-sizing:border-box; }
body { background:var(--bg); color:var(--text); font-family:-apple-system,"Microsoft YaHei","PingFang SC",sans-serif; line-height:1.6; }
a { color:var(--accent); text-decoration:none; }
.header { background:linear-gradient(135deg,#1a1b2e,#2a1b3d,#1b2a3d); border-bottom:1px solid var(--border); padding:20px 24px; }
.header h1 { font-size:22px; font-weight:700; background:linear-gradient(90deg,var(--accent),var(--accent2)); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
.header p { font-size:13px; color:var(--text3); }
.main { max-width:1000px; margin:0 auto; padding:24px; }
.back { display:inline-flex; align-items:center; gap:6px; font-size:14px; color:var(--text3); margin-bottom:16px; cursor:pointer; }
.back:hover { color:var(--accent); }
.audio-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); gap:12px; }
.audio-card { background:var(--bg2); border:1px solid var(--border); border-radius:10px; padding:14px; transition:border-color 0.2s; }
.audio-card:hover { border-color:var(--accent); }
.audio-card .thumb { width:100%; height:140px; border-radius:8px; object-fit:cover; background:var(--bg3); margin-bottom:10px; }
.audio-card .title { font-size:14px; font-weight:600; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; margin-bottom:4px; }
.audio-card .meta { font-size:12px; color:var(--text3); display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
.tag { display:inline-block; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600; }
.tag-mp3 { background:rgba(122,162,247,0.15); color:var(--accent); }
.tag-m4a { background:rgba(158,206,106,0.15); color:var(--green); }
.tag-flac { background:rgba(187,154,247,0.15); color:var(--accent2); }
.empty { text-align:center; padding:60px 20px; color:var(--text3); }
.empty .icon { font-size:48px; margin-bottom:12px; }
.rss-box { display:inline-flex; align-items:center; gap:8px; padding:8px 14px; background:var(--bg3); border-radius:8px; margin-bottom:20px; }
.rss-box a { font-size:13px; }
</style>
</head>
<body>
<div class="header">
  <h1>📂 {{ category.name }}</h1>
  {% if category.description %}<p>{{ category.description }}</p>{% endif %}
</div>
<div class="main">
  <a class="back" href="/">← 返回首页</a>
  <div class="rss-box">📡 <a href="/rss/{{ category.id }}.xml" target="_blank">RSS 订阅链接</a></div>
  <div class="audio-grid">
    {% for audio in audio_list %}
    <div class="audio-card">
      {% if audio.thumbnail %}<img class="thumb" src="{{ audio.thumbnail }}" alt="" loading="lazy">
      {% else %}<div class="thumb" style="display:flex;align-items:center;justify-content:center;font-size:40px">🎵</div>{% endif %}
      <div class="title" title="{{ audio.title }}">{{ audio.title }}</div>
      <div class="meta">
        <span class="tag tag-{{ audio.format|lower }}">{{ audio.format }}</span>
        <span>{{ audio.duration_str }}</span>
        <span>{{ audio.size_str }}</span>
      </div>
      <div class="meta" style="margin-top:4px">
        <span>{{ audio.uploader }}</span>
        <span style="margin-left:auto"><a href="{{ audio.audio_url }}" target="_blank" style="font-size:12px">▶ 播放</a></span>
      </div>
    </div>
    {% endfor %}
    {% if not audio_list %}
    <div class="empty" style="grid-column:1/-1">
      <div class="icon">📂</div>
      <div>该分类下暂无音频</div>
    </div>
    {% endif %}
  </div>
</div>
</body>
</html>
'''
