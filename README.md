# 权属管理系统

代理主体、被代理人、作品权属信息的管理平台。

## 技术栈

- 后端：Flask 3.x + SQLAlchemy (raw SQL) + PyMySQL
- 前端：Vue 3 + Vite + Element Plus + Pinia
- 数据库：MySQL（ownership_system）
- 认证：auth_client（复用现有登录体系）

## 目录结构

```
ownership_system/
├── server/
│   ├── app/              # Flask 应用
│   ├── migrations/       # init.sql 建表脚本
│   ├── uploads/          # 文件存储（自动创建）
│   ├── run.py
│   ├── requirements.txt
│   └── .env              # 配置文件（参考 .env.example）
├── client/               # Vue3 前端
├── deploy/
│   └── update.sh         # 生产环境一键更新脚本（服务器端）
└── README.md
```

## 快速启动（本地开发）

### 1. 初始化数据库

**全新安装（创建数据库和表）：**
```bash
mysql -u root -p < server/migrations/init.sql
```

### 2. 启动后端

```bash
cd server
pip install -r requirements.txt
cp .env.example .env      # 首次配置，填入数据库密码等
python run.py
```

后端默认运行在 `http://localhost:5002`（开发模式，debug=True）。

### 3. 启动前端

```bash
cd client
npm install
npm run dev
```

前端默认运行在 `http://localhost:5173`，Vite 自动代理 `/api` 到 Flask（5002）。

## 主要功能

| 模块 | 路径 | 说明 |
|------|------|------|
| 代理主体 | `/companies` | 管理公司信息和营业执照 |
| 被代理人 | `/agents` | 管理被代理人及授权委托书（含历史版本） |
| 作品 | `/works` | 管理作品及权属证明文件，支持打包下载 |

## 文件上传规则

文件超过 5MB 自动压缩（图片用 Pillow，PDF 用 Ghostscript）。后端会对上传文件做 MIME 嗅探（PNG/JPEG/GIF/BMP/PDF），如果声明的扩展名与实际二进制签名不符（如把 JPEG 改名为 .png 上传），会自动更正后缀并通过前端 `ElMessage.warning` 提示用户（默认显示 3 秒）。

| 文件类型 | 命名规则 | 存储目录 |
|---------|---------|---------|
| 代理主体营业执照 | `营业执照_{公司名}.{ext}` | `uploads/营业执照/` |
| 被代理人营业执照 | `营业执照_{被代理人名}.{ext}` | `uploads/被代理人营业执照/` |
| 授权委托书 | `授权委托书_{被代理人名}_{代理主体名}_截止{YYYYMMDD}.{ext}` | `uploads/授权委托书/` |
| 权属证明 | `权属证明_{作品名}_{uuid8}.{ext}` | `uploads/权属证明/` |
| 其他证明文件 | `其他证明_{作品名}_{序号}_{uuid8}.{ext}` | `uploads/权属证明/` |

更新授权委托书时，旧文件保留在磁盘，新文件以新截止日期命名，历史记录写入 `agent_auth_history` 表。删除被代理人 / 作品时同样记录一行 `action='delete'` 的历史，旧文件保留在磁盘，不再级联删除历史表记录。

## 数据库表结构

```
companies          — 代理主体
agents             — 被代理人（关联 companies）
agent_auth_history — 授权委托书变更历史（无 FK，被代理人删除后历史保留）
works              — 作品（关联 companies + agents）
works_history      — 作品文件变更历史（无 FK，作品删除后历史保留）
```

## 常见问题

**Q: 启动后端报数据库连接错误？**  
检查 `.env` 中的 `DB_PASSWORD` 是否正确，数据库是否已创建（`ownership_system`）。

**Q: 前端访问文件提示 404？**  
文件通过 `/api/files/{目录}/{文件名}` 访问，需要登录态。确认 `uploads/` 目录存在且后端有读写权限。

**Q: 上传文件失败，报压缩错误？**  
PDF 压缩依赖 Ghostscript，确认已安装：`gs --version`。图片压缩依赖 Pillow，已在 `requirements.txt` 中。

**Q: 不填写别名也能保存作品吗？**  
可以。`works.alias` 是可空字段（NULL），前端不填写时后端存空串，不会报错。

---

## 生产环境部署

### 环境信息

| 项 | 值 |
|---|---|
| 服务器 | `root@8.130.13.169`（Ubuntu 20.04） |
| 项目根目录 | `/opt/ownership_system/` |
| 数据库 | 阿里云公网 RDS MySQL 8.0（数据库名 `ownership_system`） |
| 访问地址 | `http://8.130.13.169:5030` |
| 进程管理 | systemd unit `ownership.service`（gunicorn） |
| 反向代理 | nginx（端口 5030 → gunicorn 5020） |

### 部署架构

```
Internet (http://8.130.13.169:5030)
   │
   ▼
┌─ nginx (sites-enabled/ownership.conf) ─┐
│  ├─ location /        → 静态文件 (Vue build)
│  └─ location /api/   → proxy_pass 127.0.0.1:5020
└─────────────────────────────────────────┘
   │
   ▼
┌─ gunicorn  127.0.0.1:5020 ─────────────┐
│  systemd: /etc/systemd/system/ownership.service
│  venv:    /opt/ownership_system/server/.venv/
└─────────────────────────────────────────┘
```

### 一键更新（代码提交后）

**本地代码推送到 GitHub 后**，SSH 登录服务器执行更新脚本即可：

```bash
ssh root@8.130.13.169
# 输入密码后进入服务器

bash /opt/ownership_system/deploy/update.sh
```

脚本会自动完成：
1. `git pull --rebase --autostash` 拉取最新代码
2. 后端依赖更新（`pip install -r requirements.txt`）
3. 前端依赖 + 构建（`npm install && npm run build`）
4. 重启后端（`systemctl restart ownership`）
5. 重载 nginx（`nginx -t && nginx -s reload`）
6. 健康检查（前端首页 + API 登录接口）

### 常用运维命令

```bash
# 查看后端运行状态
systemctl status ownership

# 实时跟踪后端日志
journalctl -u ownership -f

# 重新加载 nginx 配置（手动）
nginx -t && nginx -s reload

# 数据库迁移（首次部署）
# 服务器无 mysql client，用 .venv/bin/python3 调 pymysql 执行 server/migrations/init.sql
```

### 与服务器其他项目的隔离

- 端口 5020/5030 空闲，不与现有项目（5002/5009/5010/81/5181 等）冲突
- Python `.venv` 独立，不影响系统 Python
- nginx 配置独立文件，不动其他 server 块
- systemd unit 独立，不影响现有项目进程
