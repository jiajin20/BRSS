# deploy_config.py — BiliRSS 服务器部署配置
# 填写完毕后运行：python deploy/deploy.py

# ── 服务器信息 ──────────────────────────────────
SERVER_HOST = ''   # 服务器 IP 或域名
SERVER_USER = ''            # SSH 用户名
SERVER_PORT = 22                # SSH 端口（默认 22）

# ── 认证方式（二选一）───────────────────────────
# 方式 A：密码登录（填写密码，留空则走密钥登录）
SERVER_PASS = ''                # 例如 'MyP@ssw0rd'

# 方式 B：密钥登录（SERVER_PASS 为空时生效）
SSH_KEY_PATH = ''               # 例如 'C:/Users/jiajin/.ssh/id_rsa'
                                # 留空则自动使用 ~/.ssh/id_rsa
