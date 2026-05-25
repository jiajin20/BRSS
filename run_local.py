"""BiliRSS 本地开发入口
在项目根目录运行：python run_local.py
PyCharm 中直接右键此文件 → Run 即可
"""

from pathlib import Path

# ---- 本地数据目录（项目下的 local_data/）----
LOCAL_DATA = Path(__file__).parent / 'local_data'

# 创建必要的子目录
for sub in ['audio', 'meta', 'rss', 'cookies', 'covers']:
    (LOCAL_DATA / sub).mkdir(parents=True, exist_ok=True)

# ---- 覆盖硬编码的服务器路径 ----
# 必须在 import bili_rss.app 之前 monkey-patch，
# 因为模块顶层已经执行过路径赋值，
# 但路由函数在运行时读取的是模块全局变量，所以 patch 后依然生效。
import bili_rss.app as app_module

app_module.BASE_DIR = LOCAL_DATA
app_module.AUDIO_DIR = LOCAL_DATA / 'audio'
app_module.META_DIR = LOCAL_DATA / 'meta'
app_module.RSS_DIR = LOCAL_DATA / 'rss'
app_module.COOKIE_DIR = LOCAL_DATA / 'cookies'
app_module.COVER_DIR = LOCAL_DATA / 'covers'
app_module.DB_FILE = LOCAL_DATA / 'db.json'
app_module.BASE_URL = 'http://127.0.0.1:5000'  # 本地模式：音频 enclosure URL 指向本机

# ---- 启动 ----
print(f"[BiliRSS] 本地模式，数据目录: {LOCAL_DATA}")
app_module.app.run(host='127.0.0.1', port=5000, debug=True)
