"""重新生成 RSS，使用正确的 BASE_URL（不依赖运行中服务）"""
import sys
sys.path.insert(0, r'E:/github/BRSS')

import bili_rss.app as app

# 使用本地开发地址
app.BASE_URL = 'http://127.0.0.1:5000'
app.AUDIO_DIR = app.BASE_DIR / 'audio'
app.RSS_DIR = app.BASE_DIR / 'rss'
app.META_DIR = app.BASE_DIR / 'meta'

app.generate_rss()
print('RSS 已重新生成，BASE_URL =', app.BASE_URL)
