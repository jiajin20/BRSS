#!/usr/bin/env python3
"""Main page template for BiliRSS v3
Features: delete password, cover upload, server status, copyright page
"""

TEMPLATE_INDEX = r'''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BiliRSS - B站音频管理</title>
<style>
:root {
  --bg: #0f1117;
  --bg2: #1a1b26;
  --bg3: #24253a;
  --card: #1e1f31;
  --border: #2e3047;
  --text: #c0caf5;
  --text2: #a9b1d6;
  --text3: #787c99;
  --accent: #7aa2f7;
  --accent2: #bb9af7;
  --red: #f7768e;
  --green: #9ece6a;
  --yellow: #e0af68;
  --cyan: #7dcfff;
  --radius: 12px;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: var(--bg); color: var(--text); font-family: -apple-system, "Microsoft YaHei", "PingFang SC", sans-serif; line-height: 1.6; }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

/* Header */
.header { background: linear-gradient(135deg, #1a1b2e 0%, #2a1b3d 50%, #1b2a3d 100%); border-bottom: 1px solid var(--border); padding: 20px 0; }
.header-inner { max-width: 1200px; margin: 0 auto; padding: 0 24px; display: flex; align-items: center; justify-content: space-between; }
.logo { display: flex; align-items: center; gap: 12px; }
.logo-icon { font-size: 32px; }
.logo h1 { font-size: 24px; font-weight: 700; background: linear-gradient(90deg, var(--accent), var(--accent2)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.logo p { font-size: 13px; color: var(--text3); }
.header-stats { display: flex; gap: 24px; }
.stat-box { text-align: center; padding: 8px 16px; background: rgba(122,162,247,0.08); border-radius: 8px; }
.stat-box .num { font-size: 22px; font-weight: 700; color: var(--accent); }
.stat-box .label { font-size: 11px; color: var(--text3); }

/* Server Status Banner */
.server-banner { max-width: 1200px; margin: 0 auto; padding: 16px 24px; }
.server-status-bar { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 8px; }
.status-card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 14px 18px; display: flex; align-items: center; gap: 14px; }
.status-card .sc-icon { font-size: 28px; flex-shrink: 0; }
.status-card .sc-info { flex: 1; min-width: 0; }
.status-card .sc-label { font-size: 12px; color: var(--text3); margin-bottom: 2px; }
.status-card .sc-value { font-size: 16px; font-weight: 600; }
.status-card .sc-value.accent { color: var(--accent); }
.status-card .sc-value.green { color: var(--green); }
.status-card .sc-value.yellow { color: var(--yellow); }
.status-card .sc-value.cyan { color: var(--cyan); }
.disk-bar { height: 6px; background: var(--bg3); border-radius: 3px; overflow: hidden; margin-top: 6px; }
.disk-bar .fill { height: 100%; border-radius: 3px; transition: width 0.5s; }
.disk-bar .fill.green { background: var(--green); }
.disk-bar .fill.yellow { background: var(--yellow); }
.disk-bar .fill.red { background: var(--red); }

/* Tab Navigation */
.tabs { max-width: 1200px; margin: 0 auto; padding: 0 24px; display: flex; gap: 4px; border-bottom: 1px solid var(--border); }
.tab-btn { padding: 10px 20px; background: none; border: none; color: var(--text3); font-size: 14px; font-weight: 500; cursor: pointer; border-bottom: 2px solid transparent; transition: all 0.2s; font-family: inherit; }
.tab-btn:hover { color: var(--text); }
.tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); }

/* Main Content */
.main { max-width: 1200px; margin: 0 auto; padding: 24px; }
.tab-content { display: none; }
.tab-content.active { display: block; }

/* Cards */
.card { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); padding: 20px; margin-bottom: 16px; }
.card-title { font-size: 16px; font-weight: 600; color: var(--text); margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
.card-title .icon { font-size: 18px; }

/* Buttons */
.btn { padding: 8px 16px; border-radius: 8px; border: none; font-size: 13px; font-weight: 500; cursor: pointer; transition: all 0.2s; font-family: inherit; display: inline-flex; align-items: center; gap: 6px; }
.btn-primary { background: var(--accent); color: #fff; }
.btn-primary:hover { background: #6b91e0; }
.btn-danger { background: var(--red); color: #fff; opacity: 0.85; }
.btn-danger:hover { opacity: 1; }
.btn-ghost { background: transparent; border: 1px solid var(--border); color: var(--text2); }
.btn-ghost:hover { border-color: var(--accent); color: var(--accent); }
.btn-sm { padding: 5px 10px; font-size: 12px; }
.btn-accent2 { background: var(--accent2); color: #fff; }
.btn-accent2:hover { background: #a081e0; }
.btn-green { background: var(--green); color: #1a1b26; }

/* Forms */
.form-group { margin-bottom: 14px; }
.form-group label { display: block; font-size: 13px; color: var(--text2); margin-bottom: 6px; font-weight: 500; }
input[type="text"], input[type="url"], input[type="password"], textarea, select {
  width: 100%; padding: 10px 12px; background: var(--bg2); border: 1px solid var(--border);
  border-radius: 8px; color: var(--text); font-size: 14px; font-family: inherit; transition: border 0.2s;
}
input:focus, textarea:focus, select:focus { outline: none; border-color: var(--accent); }
select { appearance: none; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' fill='%23a9b1d6'%3E%3Cpath d='M6 8L1 3h10z'/%3E%3C/svg%3E"); background-repeat: no-repeat; background-position: right 12px center; padding-right: 32px; }
textarea { resize: vertical; min-height: 60px; }
input[type="file"] { font-size: 13px; color: var(--text2); }
input[type="file"]::file-selector-button { background: var(--bg3); border: 1px solid var(--border); color: var(--text2); padding: 6px 14px; border-radius: 6px; cursor: pointer; font-family: inherit; margin-right: 8px; }
input[type="file"]::file-selector-button:hover { border-color: var(--accent); color: var(--accent); }

/* Grid */
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }

/* Tags */
.tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.tag-mp3 { background: rgba(122,162,247,0.15); color: var(--accent); }
.tag-flac { background: rgba(187,154,247,0.15); color: var(--accent2); }
.tag-m4a { background: rgba(158,206,106,0.15); color: var(--green); }
.tag-opus { background: rgba(125,207,255,0.15); color: var(--cyan); }
.tag-wav { background: rgba(224,175,104,0.15); color: var(--yellow); }
.tag-locked { background: rgba(247,118,142,0.15); color: var(--red); }
.tag-unlocked { background: rgba(158,206,106,0.15); color: var(--green); }

/* Audio Item */
.audio-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }
.audio-card { background: var(--bg2); border: 1px solid var(--border); border-radius: 10px; padding: 14px; transition: border-color 0.2s; position: relative; }
.audio-card:hover { border-color: var(--accent); }
.audio-card .thumb { width: 100%; height: 140px; border-radius: 8px; object-fit: cover; background: var(--bg3); margin-bottom: 10px; }
.audio-card .title { font-size: 14px; font-weight: 600; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-bottom: 4px; }
.audio-card .meta { font-size: 12px; color: var(--text3); display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.audio-card .actions { position: absolute; top: 8px; right: 8px; display: flex; gap: 4px; opacity: 0; transition: opacity 0.2s; }
.audio-card:hover .actions { opacity: 1; }
.audio-card .add-col-btn { padding: 4px 8px; background: var(--accent2); color: #fff; border: none; border-radius: 4px; font-size: 11px; cursor: pointer; }

/* Task Item */
.task-item { display: flex; align-items: center; padding: 12px 16px; background: var(--bg2); border: 1px solid var(--border); border-radius: 10px; margin-bottom: 8px; gap: 12px; }
.task-item .task-icon { font-size: 20px; flex-shrink: 0; }
.task-item .task-info { flex: 1; min-width: 0; }
.task-item .task-name { font-size: 14px; font-weight: 500; }
.task-item .task-meta { font-size: 12px; color: var(--text3); display: flex; gap: 12px; }
.task-item .task-actions { display: flex; gap: 6px; flex-shrink: 0; }

.status-running { color: var(--yellow); }
.status-completed { color: var(--green); }
.status-failed { color: var(--red); }
.status-pending { color: var(--text3); }

/* Collection Card */
.col-card { background: var(--bg2); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
.col-card .col-cover { width: 100%; height: 160px; object-fit: cover; background: linear-gradient(135deg, var(--bg3), var(--card)); display: flex; align-items: center; justify-content: center; }
.col-card .col-cover img { width: 100%; height: 100%; object-fit: cover; }
.col-card .col-cover .no-cover { font-size: 48px; opacity: 0.5; }
.col-card .col-body { padding: 16px; }
.col-card .col-header { display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px; }
.col-card .col-name { font-size: 15px; font-weight: 600; }
.col-card .col-desc { font-size: 12px; color: var(--text3); margin-bottom: 8px; }
.col-card .col-items { font-size: 12px; color: var(--text2); }
.col-card .col-actions { display: flex; gap: 6px; flex-wrap: wrap; }
.col-card .cover-upload-area { position: relative; }
.col-card .cover-upload-btn { position: absolute; bottom: 8px; right: 8px; padding: 4px 10px; background: rgba(0,0,0,0.7); color: #fff; border: none; border-radius: 4px; font-size: 11px; cursor: pointer; opacity: 0; transition: opacity 0.2s; }
.col-card:hover .cover-upload-btn { opacity: 1; }

/* Search */
.search-bar { display: flex; gap: 8px; margin-bottom: 16px; }
.search-bar input { flex: 1; }

/* Modal */
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 1000; display: flex; align-items: center; justify-content: center; display: none; }
.modal-overlay.show { display: flex; }
.modal { background: var(--card); border: 1px solid var(--border); border-radius: var(--radius); padding: 24px; width: 90%; max-width: 500px; max-height: 80vh; overflow-y: auto; }
.modal h3 { font-size: 18px; font-weight: 600; margin-bottom: 16px; }
.modal .modal-close { float: right; background: none; border: none; color: var(--text3); font-size: 20px; cursor: pointer; }

/* Toast */
.toast { position: fixed; top: 20px; right: 20px; padding: 12px 20px; border-radius: 8px; font-size: 14px; z-index: 2000; opacity: 0; transform: translateY(-10px); transition: all 0.3s; }
.toast.show { opacity: 1; transform: translateY(0); }
.toast-success { background: var(--green); color: #1a1b26; }
.toast-error { background: var(--red); color: #fff; }

/* Progress bar */
.progress-bar { height: 4px; background: var(--bg3); border-radius: 2px; overflow: hidden; margin-top: 6px; }
.progress-bar .fill { height: 100%; background: var(--accent); border-radius: 2px; transition: width 0.3s; }

/* RSS links */
.rss-link { display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: var(--bg2); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 6px; }
.rss-link .rss-icon { color: var(--yellow); font-size: 16px; }
.rss-link a { flex: 1; font-size: 13px; }
.rss-link .copy-btn { padding: 3px 8px; background: var(--bg3); border: 1px solid var(--border); border-radius: 4px; color: var(--text3); font-size: 11px; cursor: pointer; }
.rss-link .copy-btn:hover { color: var(--accent); border-color: var(--accent); }

/* Checkbox list for adding to collection */
.check-list { max-height: 300px; overflow-y: auto; }
.check-item { display: flex; align-items: center; gap: 8px; padding: 6px 8px; border-radius: 6px; }
.check-item:hover { background: var(--bg3); }
.check-item input[type="checkbox"] { accent-color: var(--accent); }
.check-item .check-label { font-size: 13px; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* Responsive */
@media (max-width: 768px) {
  .grid-2, .grid-3 { grid-template-columns: 1fr; }
  .header-inner { flex-direction: column; gap: 12px; }
  .audio-grid { grid-template-columns: 1fr; }
  .server-status-bar { grid-template-columns: 1fr 1fr; }
}

/* Inline form rows */
.form-row { display: flex; gap: 12px; align-items: end; }
.form-row .form-group { flex: 1; margin-bottom: 0; }

/* Empty state */
.empty { text-align: center; padding: 40px 20px; color: var(--text3); }
.empty .empty-icon { font-size: 48px; margin-bottom: 12px; }

/* Section header */
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.section-header h2 { font-size: 18px; font-weight: 600; }

/* Auto-refresh status */
.status-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
.status-dot.running { background: var(--yellow); animation: pulse 1.5s infinite; }
.status-dot.completed { background: var(--green); }
.status-dot.failed { background: var(--red); }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

/* Collection audio item */
.col-audio-item { display: flex; align-items: center; gap: 10px; padding: 8px; background: var(--bg3); border-radius: 6px; margin-bottom: 4px; }
.col-audio-item .col-audio-title { flex: 1; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.col-audio-item .col-audio-meta { font-size: 11px; color: var(--text3); }

/* Footer */
.footer { max-width: 1200px; margin: 40px auto 0; padding: 24px; border-top: 1px solid var(--border); }
.footer-inner { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }
.footer-left { display: flex; align-items: center; gap: 12px; }
.footer-logo { font-size: 20px; }
.footer-text { font-size: 13px; color: var(--text3); }
.footer-text a { color: var(--accent); }
.footer-text a:hover { text-decoration: underline; }
.footer-right { font-size: 12px; color: var(--text3); }
.footer-links { display: flex; gap: 16px; }
.footer-links a { font-size: 13px; color: var(--text3); }
.footer-links a:hover { color: var(--accent); }

/* Password modal */
.password-hint { display: flex; align-items: center; gap: 8px; padding: 10px 14px; background: rgba(247,118,142,0.1); border: 1px solid rgba(247,118,142,0.2); border-radius: 8px; margin-bottom: 14px; font-size: 13px; color: var(--red); }
</style>
</head>
<body>

<!-- Header -->
<div class="header">
  <div class="header-inner">
    <div class="logo">
      <span class="logo-icon">🎧</span>
      <div>
        <h1>BiliRSS</h1>
        <p>B站音频下载 & RSS 管理</p>
      </div>
    </div>
    <div class="header-stats">
      <div class="stat-box">
        <div class="num">{{ total_audio }}</div>
        <div class="label">音频文件</div>
      </div>
      <div class="stat-box">
        <div class="num">{{ total_size_str }}</div>
        <div class="label">总大小</div>
      </div>
      <div class="stat-box">
        <div class="num">{{ categories|length }}</div>
        <div class="label">分类</div>
      </div>
      <div class="stat-box">
        <div class="num">{{ total_collections }}</div>
        <div class="label">合集</div>
      </div>
    </div>
  </div>
</div>

<!-- Server Status Banner -->
<div class="server-banner">
  <div class="server-status-bar">
    <div class="status-card">
      <div class="sc-icon">💾</div>
      <div class="sc-info">
        <div class="sc-label">磁盘空间</div>
        <div class="sc-value accent">{{ server_status.disk_used }} / {{ server_status.disk_total }}</div>
        <div class="disk-bar"><div class="fill {% if server_status.disk_percent < 70 %}green{% elif server_status.disk_percent < 90 %}yellow{% else %}red{% endif %}" style="width:{{ server_status.disk_percent }}%"></div></div>
        <div style="font-size:11px;color:var(--text3);margin-top:2px">剩余 {{ server_status.disk_free }}（{{ server_status.disk_percent }}% 已用）</div>
      </div>
    </div>
    <div class="status-card">
      <div class="sc-icon">🎵</div>
      <div class="sc-info">
        <div class="sc-label">音频资源</div>
        <div class="sc-value green">{{ total_audio }} 首音频 · {{ total_collections }} 个合集</div>
      </div>
    </div>
    <div class="status-card">
      <div class="sc-icon">⏱️</div>
      <div class="sc-info">
        <div class="sc-label">服务运行时长</div>
        <div class="sc-value cyan">{{ server_status.uptime }}</div>
      </div>
    </div>
  </div>
</div>

<!-- Tab Navigation -->
<div class="tabs">
  <button class="tab-btn active" onclick="switchTab('download')">📥 下载管理</button>
  <button class="tab-btn" onclick="switchTab('files')">📁 文件管理</button>
  <button class="tab-btn" onclick="switchTab('collections')">🎵 合集管理</button>
  <button class="tab-btn" onclick="switchTab('rss')">📡 RSS 订阅</button>
</div>

<!-- Main Content -->
<div class="main">

<!-- ========== Tab: Download ========== -->
<div class="tab-content active" id="tab-download">
  <div class="grid-2">
    <!-- Left: New Task -->
    <div class="card">
      <div class="card-title"><span class="icon">➕</span> 新建下载任务</div>
      <form id="taskForm" onsubmit="return submitTask(event)">
        <div class="form-group">
          <label>下载类型</label>
          <select id="url_type" onchange="toggleUidHint()">
            <option value="video">单个视频（BV号/链接）</option>
            <option value="up">UP主全部视频</option>
          </select>
        </div>
        <div class="form-group">
          <label id="url_label">视频链接 / BV号</label>
          <input type="text" id="url" placeholder="例如: BV1CdLq6WEod 或 https://www.bilibili.com/video/BV1CdLq6WEod">
          <div id="uid_hint" style="display:none;font-size:12px;color:var(--text3);margin-top:4px;">输入 UP主 UID 或主页链接，例如: 3493127314737312</div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>所属分类</label>
            <select id="category_id">
              {% for cat in categories %}
              <option value="{{ cat.id }}">{{ cat.name }}</option>
              {% endfor %}
            </select>
          </div>
          <div class="form-group">
            <label>音频格式</label>
            <select id="audio_format">
              {% for key, label in format_options.items() %}
              <option value="{{ key }}" {% if key == 'mp3' %}selected{% endif %}>{{ label }}</option>
              {% endfor %}
            </select>
          </div>
        </div>
        <div class="form-group">
          <label>B站 Cookie（可选，全局共享）</label>
          <input type="text" id="cookie" placeholder="留空则使用已保存的全局 Cookie">
        </div>
        <button type="submit" class="btn btn-primary" style="width:100%">🚀 开始下载</button>
      </form>

      <hr style="border:none;border-top:1px solid var(--border);margin:20px 0 16px">
      <div class="card-title" style="font-size:14px"><span class="icon">📂</span> 新建分类</div>
      <form id="catForm" onsubmit="return submitCategory(event)" style="display:flex;gap:8px">
        <input type="text" id="cat_name" placeholder="分类名称" style="flex:2">
        <input type="text" id="cat_desc" placeholder="描述（可选）" style="flex:3">
        <button type="submit" class="btn btn-ghost">创建</button>
      </form>

      <!-- Category List -->
      <div style="margin-top:12px">
        {% for cat in categories %}
        <div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--border)">
          <span style="flex:1;font-size:13px">📂 {{ cat.name }} <span style="color:var(--text3)">{{ cat.audio_count }}首</span></span>
          <button class="btn btn-sm btn-danger" onclick="deleteCategory('{{ cat.id }}')">删除</button>
        </div>
        {% endfor %}
        {% if not categories %}
        <div style="font-size:13px;color:var(--text3);padding:8px 0">还没有分类，请先创建一个</div>
        {% endif %}
      </div>
    </div>

    <!-- Right: Task List -->
    <div class="card">
      <div class="card-title"><span class="icon">📋</span> 下载任务</div>
      <div id="taskList">
        {% for task in tasks %}
        <div class="task-item" id="task-{{ task.id }}">
          <span class="task-icon">{% if task.url_type == 'up' %}👤{% else %}🎬{% endif %}</span>
          <div class="task-info">
            <div class="task-name">{{ task.name }}</div>
            <div class="task-meta">
              <span>{{ task.category_name }}</span>
              <span>{{ task.created_at[:16] }}</span>
              <span id="task-status-{{ task.id }}">
                <span class="status-dot {{ task.dl_status }}"></span>
                <span class="status-{{ task.dl_status }}">{{ task.dl_message or task.dl_status }}</span>
              </span>
            </div>
          </div>
          <div class="task-actions">
            <button class="btn btn-sm btn-ghost" onclick="redownload('{{ task.id }}')" title="重新下载">🔄</button>
            <button class="btn btn-sm btn-danger" onclick="deleteTask('{{ task.id }}')" title="删除">✕</button>
          </div>
        </div>
        {% endfor %}
        {% if not tasks %}
        <div class="empty">
          <div class="empty-icon">📥</div>
          <div>暂无下载任务</div>
        </div>
        {% endif %}
      </div>
    </div>
  </div>
</div>

<!-- ========== Tab: Files ========== -->
<div class="tab-content" id="tab-files">
  <div class="section-header">
    <h2>📁 音频文件库</h2>
    <div style="display:flex;gap:8px;align-items:center">
      <select id="formatFilter" onchange="filterFiles()" style="width:120px;padding:6px 10px">
        <option value="">全部格式</option>
        <option value="MP3">MP3</option>
        <option value="FLAC">FLAC</option>
        <option value="M4A">M4A</option>
        <option value="OPUS">OPUS</option>
        <option value="WAV">WAV</option>
      </select>
      <input type="text" id="fileSearch" placeholder="🔍 搜索标题 / BV号 / UP主..." oninput="filterFiles()" style="width:240px">
    </div>
  </div>
  <div class="audio-grid" id="audioGrid">
    {% for audio in audio_list %}
    <div class="audio-card" data-bvid="{{ audio.bv_id }}" data-title="{{ audio.title|lower }}" data-uploader="{{ audio.uploader|lower }}" data-format="{{ audio.format }}">
      {% if audio.thumbnail %}
      <img class="thumb" src="{{ audio.thumbnail }}" alt="" loading="lazy">
      {% else %}
      <div class="thumb" style="display:flex;align-items:center;justify-content:center;font-size:40px">🎵</div>
      {% endif %}
      <div class="actions">
        <button class="add-col-btn" onclick="showAddToCollection('{{ audio.bv_id }}')">+ 合集</button>
      </div>
      <div class="title" title="{{ audio.title }}">{{ audio.title }}</div>
      <div class="meta">
        <span class="tag tag-{{ audio.format|lower }}">{{ audio.format }}</span>
        <span>{{ audio.duration_str }}</span>
        <span>{{ audio.size_str }}</span>
      </div>
      <div class="meta" style="margin-top:4px">
        <span>{{ audio.uploader }}</span>
        <span style="margin-left:auto">
          <a href="{{ audio.audio_url }}" target="_blank" style="font-size:12px">▶ 播放</a>
          <a href="#" onclick="deleteAudio('{{ audio.bv_id }}');return false" style="font-size:12px;color:var(--red);margin-left:8px">删除</a>
        </span>
      </div>
    </div>
    {% endfor %}
    {% if not audio_list %}
    <div class="empty" style="grid-column:1/-1">
      <div class="empty-icon">📁</div>
      <div>还没有下载任何音频文件</div>
    </div>
    {% endif %}
  </div>
</div>

<!-- ========== Tab: Collections ========== -->
<div class="tab-content" id="tab-collections">
  <div class="section-header">
    <h2>🎵 合集管理</h2>
    <button class="btn btn-primary" onclick="showModal('newColModal')">➕ 新建合集</button>
  </div>

  <!-- New Collection Form (modal) -->
  <div class="modal-overlay" id="newColModal">
    <div class="modal">
      <button class="modal-close" onclick="hideModal('newColModal')">×</button>
      <h3>🎵 新建合集</h3>
      <form onsubmit="return submitCollection(event)">
        <div class="form-group">
          <label>合集名称 *</label>
          <input type="text" id="col_name" placeholder="例如：睡前故事合集" required>
        </div>
        <div class="form-group">
          <label>合集描述</label>
          <textarea id="col_desc" placeholder="可选，描述此合集的内容"></textarea>
        </div>
        <div class="form-group">
          <label>🔒 删除密码（可选）</label>
          <input type="password" id="col_delete_password" placeholder="设置后删除合集时需验证密码">
          <div style="font-size:12px;color:var(--text3);margin-top:4px">留空则不设密码保护，RSS 订阅不受影响</div>
        </div>
        <button type="submit" class="btn btn-primary" style="width:100%">创建合集</button>
      </form>
    </div>
  </div>

  <!-- Delete with Password Modal -->
  <div class="modal-overlay" id="deleteColModal">
    <div class="modal">
      <button class="modal-close" onclick="hideModal('deleteColModal')">×</button>
      <h3>🔒 验证删除密码</h3>
      <div class="password-hint">
        <span>⚠️</span>
        <span>此合集设有删除密码保护，请输入密码后确认删除</span>
      </div>
      <form onsubmit="return confirmDeleteCollection(event)">
        <div class="form-group">
          <label>删除密码</label>
          <input type="password" id="delete_col_password" placeholder="请输入删除密码" required>
        </div>
        <input type="hidden" id="delete_col_id">
        <div style="display:flex;gap:8px">
          <button type="button" class="btn btn-ghost" style="flex:1" onclick="hideModal('deleteColModal')">取消</button>
          <button type="submit" class="btn btn-danger" style="flex:1">确认删除</button>
        </div>
      </form>
    </div>
  </div>

  <!-- Add to Collection Modal -->
  <div class="modal-overlay" id="addColModal">
    <div class="modal">
      <button class="modal-close" onclick="hideModal('addColModal')">×</button>
      <h3>添加到合集</h3>
      <div id="addColBvIds" style="display:none"></div>
      <p style="font-size:13px;color:var(--text3);margin-bottom:12px">选择要添加到的合集：</p>
      <div id="addColList">
        {% for col in collections %}
        <div style="display:flex;align-items:center;gap:8px;padding:8px;border-radius:6px;cursor:pointer" onclick="addToCollection('{{ col.id }}')" onmouseover="this.style.background='var(--bg3)'" onmouseout="this.style.background='transparent'">
          <span>🎵</span>
          <span style="flex:1;font-size:14px">{{ col.name }}</span>
          <span style="font-size:12px;color:var(--text3)">{{ col.bv_ids|length }}首</span>
        </div>
        {% endfor %}
        {% if not collections %}
        <div style="font-size:13px;color:var(--text3);padding:12px">还没有合集，请先创建</div>
        {% endif %}
      </div>
    </div>
  </div>

  <!-- Collection List -->
  <div class="grid-2">
    {% for col in collections %}
    <div class="col-card" id="col-{{ col.id }}">
      <!-- Cover -->
      <div class="col-cover cover-upload-area">
        {% if col.cover %}
        <img src="/covers/{{ col.cover }}" alt="{{ col.name }}">
        {% else %}
        <div class="no-cover">🎵</div>
        {% endif %}
        <label class="cover-upload-btn" for="cover-{{ col.id }}">📷 更换封面</label>
        <input type="file" id="cover-{{ col.id }}" accept="image/*" style="display:none" onchange="uploadCover('{{ col.id }}', this)">
      </div>
      <div class="col-body">
        <div class="col-header">
          <div>
            <div class="col-name">
              🎵 {{ col.name }}
              {% if col.delete_password %}
              <span class="tag tag-locked" title="已设置删除密码保护">🔒 密码保护</span>
              {% else %}
              <span class="tag tag-unlocked" title="未设置密码保护">🔓 无密码</span>
              {% endif %}
            </div>
            {% if col.description %}<div class="col-desc">{{ col.description }}</div>{% endif %}
          </div>
          <div class="col-actions">
            <button class="btn btn-sm btn-ghost" onclick="copyRssUrl('col_{{ col.id }}.xml')" title="复制 RSS 链接">📡</button>
            <button class="btn btn-sm btn-danger" onclick="deleteCollection('{{ col.id }}')">删除</button>
          </div>
        </div>
        <div class="col-items">
          {% for bv_id in col.bv_ids[:5] %}
          <div class="col-audio-item">
            <span style="font-size:12px;color:var(--text3)">{{ loop.index }}.</span>
            <span class="col-audio-title">{% set audio_info = namespace(found=false) %}{% for a in audio_list %}{% if a.bv_id == bv_id %}{{ a.title }}{% set audio_info.found = true %}{% endif %}{% endfor %}{% if not audio_info.found %}{{ bv_id }}{% endif %}</span>
            <button class="btn btn-sm btn-danger" style="padding:2px 6px;font-size:10px" onclick="removeFromCollection('{{ col.id }}','{{ bv_id }}')">✕</button>
          </div>
          {% endfor %}
          {% if col.bv_ids|length > 5 %}
          <div style="font-size:12px;color:var(--text3);padding:4px 8px">...还有 {{ col.bv_ids|length - 5 }} 首</div>
          {% endif %}
          {% if not col.bv_ids %}
          <div style="font-size:12px;color:var(--text3);padding:8px">空合集，从文件管理添加音频</div>
          {% endif %}
        </div>
      </div>
    </div>
    {% endfor %}
    {% if not collections %}
    <div class="empty" style="grid-column:1/-1">
      <div class="empty-icon">🎵</div>
      <div>还没有合集，点击右上角创建</div>
    </div>
    {% endif %}
  </div>
</div>

<!-- ========== Tab: RSS ========== -->
<div class="tab-content" id="tab-rss">
  <div class="section-header">
    <h2>📡 RSS 订阅源</h2>
    <button class="btn btn-primary" onclick="regenerateRss()">🔄 重新生成</button>
  </div>

  <div class="card">
    <div class="card-title">全局 RSS</div>
    <div class="rss-link">
      <span class="rss-icon">📡</span>
      <a href="/rss/all.xml" target="_blank">全部音频</a>
      <button class="copy-btn" onclick="copyRssUrl('all.xml')">复制链接</button>
    </div>
  </div>

  <div class="card">
    <div class="card-title">按分类 RSS</div>
    {% for cat in categories %}
    <div class="rss-link">
      <span class="rss-icon">📂</span>
      <a href="/rss/{{ cat.id }}.xml" target="_blank">{{ cat.name }}</a>
      <button class="copy-btn" onclick="copyRssUrl('{{ cat.id }}.xml')">复制链接</button>
    </div>
    {% endfor %}
    {% if not categories %}
    <div style="font-size:13px;color:var(--text3)">暂无分类</div>
    {% endif %}
  </div>

  <div class="card">
    <div class="card-title">按合集 RSS</div>
    {% for col in collections %}
    <div class="rss-link">
      <span class="rss-icon">🎵</span>
      {% if col.cover %}
      <img src="/covers/{{ col.cover }}" style="width:24px;height:24px;border-radius:4px;object-fit:cover" alt="">
      {% endif %}
      <a href="/rss/col_{{ col.id }}.xml" target="_blank">{{ col.name }}</a>
      <button class="copy-btn" onclick="copyRssUrl('col_{{ col.id }}.xml')">复制链接</button>
    </div>
    {% endfor %}
    {% if not collections %}
    <div style="font-size:13px;color:var(--text3)">暂无合集</div>
    {% endif %}
  </div>
</div>

</div><!-- /.main -->

<!-- Footer / Copyright -->
<div class="footer">
  <div class="footer-inner">
    <div class="footer-left">
      <span class="footer-logo">🎧</span>
      <div class="footer-text">
        <strong>BiliRSS</strong> · B站音频下载 & RSS 管理系统<br>
        开发：<a href="https://github.com/jiajin20" target="_blank">jiajin20</a> ·
        GitHub：<a href="https://github.com/jiajin20" target="_blank">github.com/jiajin20</a>
      </div>
    </div>
    <div class="footer-right">
      <div class="footer-links">
        <a href="https://github.com/jiajin20" target="_blank">GitHub</a>
        <span style="color:var(--text3)">© 2025 BiliRSS</span>
      </div>
    </div>
  </div>
</div>

<!-- Toast -->
<div class="toast" id="toast"></div>

<script>
// === Tab Switching ===
function switchTab(name) {
  document.querySelectorAll('.tab-btn').forEach((b,i) => b.classList.toggle('active', ['download','files','collections','rss'][i] === name));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
}

// === Toast ===
function showToast(msg, type='success') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast toast-' + type + ' show';
  setTimeout(() => t.classList.remove('show'), 3000);
}

// === Modal ===
function showModal(id) { document.getElementById(id).classList.add('show'); }
function hideModal(id) { document.getElementById(id).classList.remove('show'); }

// === Toggle UID hint ===
function toggleUidHint() {
  const isUp = document.getElementById('url_type').value === 'up';
  document.getElementById('uid_hint').style.display = isUp ? 'block' : 'none';
  document.getElementById('url_label').textContent = isUp ? 'UP主 UID / 主页链接' : '视频链接 / BV号';
  document.getElementById('url').placeholder = isUp ? '例如: 3493127314737312' : '例如: BV1CdLq6WEod 或 https://www.bilibili.com/video/BV1CdLq6WEod';
}

// === Submit Task ===
async function submitTask(e) {
  e.preventDefault();
  const form = new FormData();
  form.append('url_type', document.getElementById('url_type').value);
  form.append('url', document.getElementById('url').value);
  form.append('category_id', document.getElementById('category_id').value);
  form.append('audio_format', document.getElementById('audio_format').value);
  form.append('cookie', document.getElementById('cookie').value);
  const resp = await fetch('/api/task', { method: 'POST', body: form });
  const data = await resp.json();
  if (data.ok) { showToast('下载任务已创建！'); setTimeout(() => location.reload(), 1500); }
  else showToast(data.error || '创建失败', 'error');
  return false;
}

// === Submit Category ===
async function submitCategory(e) {
  e.preventDefault();
  const form = new FormData();
  form.append('name', document.getElementById('cat_name').value);
  form.append('description', document.getElementById('cat_desc').value);
  const resp = await fetch('/api/category', { method: 'POST', body: form });
  const data = await resp.json();
  if (data.ok) { showToast('分类已创建！'); setTimeout(() => location.reload(), 800); }
  else showToast(data.error || '创建失败', 'error');
  return false;
}

// === Submit Collection (with delete password) ===
async function submitCollection(e) {
  e.preventDefault();
  const form = new FormData();
  form.append('name', document.getElementById('col_name').value);
  form.append('description', document.getElementById('col_desc').value);
  form.append('delete_password', document.getElementById('col_delete_password').value);
  const resp = await fetch('/api/collection', { method: 'POST', body: form });
  const data = await resp.json();
  if (data.ok) { hideModal('newColModal'); showToast('合集已创建！'); setTimeout(() => location.reload(), 800); }
  else showToast(data.error || '创建失败', 'error');
  return false;
}

// === Delete with password check ===
let pendingDeleteColId = null;

async function deleteCollection(colId) {
  pendingDeleteColId = colId;
  // First, try to delete without password
  const form = new FormData();
  const resp = await fetch('/api/collection/' + colId, { method: 'DELETE', body: form });
  const data = await resp.json();

  if (data.need_password) {
    // Show password modal
    document.getElementById('delete_col_id').value = colId;
    document.getElementById('delete_col_password').value = '';
    showModal('deleteColModal');
  } else if (data.ok) {
    showToast('合集已删除');
    setTimeout(() => location.reload(), 800);
  } else {
    showToast(data.error || '删除失败', 'error');
  }
}

async function confirmDeleteCollection(e) {
  e.preventDefault();
  const colId = document.getElementById('delete_col_id').value;
  const password = document.getElementById('delete_col_password').value;
  const form = new FormData();
  form.append('password', password);
  const resp = await fetch('/api/collection/' + colId, { method: 'DELETE', body: form });
  const data = await resp.json();
  if (data.ok) {
    hideModal('deleteColModal');
    showToast('合集已删除');
    setTimeout(() => location.reload(), 800);
  } else {
    showToast(data.error || '密码错误', 'error');
  }
  return false;
}

// === Delete Category/Task/Audio ===
async function deleteCategory(id) {
  if (!confirm('确定要删除此分类吗？关联的下载任务也会被删除。')) return;
  await fetch('/api/category/' + id, { method: 'DELETE' });
  showToast('分类已删除'); setTimeout(() => location.reload(), 800);
}
async function deleteTask(id) {
  if (!confirm('确定要删除此任务吗？')) return;
  await fetch('/api/task/' + id, { method: 'DELETE' });
  showToast('任务已删除'); setTimeout(() => location.reload(), 800);
}
async function deleteAudio(bvId) {
  if (!confirm('确定要删除此音频文件吗？')) return;
  await fetch('/api/audio/' + bvId, { method: 'DELETE' });
  showToast('音频已删除'); setTimeout(() => location.reload(), 800);
}

// === Re-download ===
async function redownload(id) {
  await fetch('/api/task/' + id + '/download', { method: 'POST' });
  showToast('重新下载已开始');
  pollStatus();
}

// === Add to Collection ===
let pendingBvIds = [];
function showAddToCollection(bvId) {
  pendingBvIds = [bvId];
  document.getElementById('addColBvIds').textContent = bvId;
  showModal('addColModal');
}
async function addToCollection(colId) {
  const form = new FormData();
  form.append('bv_ids', pendingBvIds.join(','));
  await fetch('/api/collection/' + colId + '/add', { method: 'POST', body: form });
  hideModal('addColModal');
  showToast('已添加到合集！'); setTimeout(() => location.reload(), 800);
}
async function removeFromCollection(colId, bvId) {
  const form = new FormData();
  form.append('bv_ids', bvId);
  await fetch('/api/collection/' + colId + '/remove', { method: 'POST', body: form });
  showToast('已从合集移除'); setTimeout(() => location.reload(), 800);
}

// === Cover Upload ===
async function uploadCover(colId, input) {
  if (!input.files || !input.files[0]) return;
  const form = new FormData();
  form.append('cover', input.files[0]);
  try {
    const resp = await fetch('/api/collection/' + colId + '/cover', { method: 'POST', body: form });
    const data = await resp.json();
    if (data.ok) {
      showToast('封面已更新！');
      setTimeout(() => location.reload(), 800);
    } else {
      showToast(data.error || '上传失败', 'error');
    }
  } catch(e) {
    showToast('上传失败', 'error');
  }
}

// === RSS ===
async function regenerateRss() {
  const resp = await fetch('/api/rss/regenerate', { method: 'POST' });
  const data = await resp.json();
  if (data.ok) showToast('RSS 已重新生成！');
}
function copyRssUrl(filename) {
  const url = location.origin + '/rss/' + filename;
  navigator.clipboard.writeText(url).then(() => showToast('RSS 链接已复制！')).catch(() => showToast('复制失败', 'error'));
}

// === File Filter ===
function filterFiles() {
  const search = document.getElementById('fileSearch').value.toLowerCase();
  const fmt = document.getElementById('formatFilter').value;
  document.querySelectorAll('.audio-card').forEach(card => {
    const title = card.dataset.title || '';
    const uploader = card.dataset.uploader || '';
    const bvid = card.dataset.bvid || '';
    const format = card.dataset.format || '';
    const matchSearch = !search || title.includes(search) || bvid.toLowerCase().includes(search) || uploader.includes(search);
    const matchFormat = !fmt || format === fmt;
    card.style.display = (matchSearch && matchFormat) ? '' : 'none';
  });
}

// === Status Polling ===
let polling = false;
async function pollStatus() {
  if (polling) return;
  polling = true;
  while (true) {
    try {
      const resp = await fetch('/api/status');
      const status = await resp.json();
      let hasRunning = false;
      for (const [id, s] of Object.entries(status)) {
        if (s.status === 'running') hasRunning = true;
        const el = document.getElementById('task-status-' + id);
        if (el) {
          el.innerHTML = '<span class="status-dot ' + s.status + '"></span><span class="status-' + s.status + '">' + s.message + '</span>';
        }
      }
      if (!hasRunning) break;
      await new Promise(r => setTimeout(r, 3000));
    } catch { break; }
  }
  polling = false;
}

// Start polling if any running tasks
{% for task in tasks %}
{% if task.dl_status == 'running' %}
pollStatus();
{% endif %}
{% endfor %}
</script>
</body>
</html>
'''
