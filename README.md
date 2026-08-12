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
└── README.md
```

## 快速启动

### 1. 初始化数据库

**全新安装（创建数据库和表）：**
```bash
mysql -u root -p < server/migrations/init.sql
```

**已有数据库，仅补充注释：**
```bash
mysql -u root -p ownership_system < alter_comments.sql
```

### 2. 启动后端

```bash
cd server
pip install -r requirements.txt
cp .env.example .env      # 首次配置，填入数据库密码等
python run.py
```

后端默认运行在 `http://localhost:5000`

### 3. 启动前端

```bash
cd client
npm install
npm run dev
```

前端默认运行在 `http://localhost:5173`，Vite 自动代理 `/api` 到 Flask。

## 主要功能

| 模块 | 路径 | 说明 |
|------|------|------|
| 代理主体 | `/companies` | 管理公司信息和营业执照 |
| 被代理人 | `/agents` | 管理被代理人及授权委托书（含历史版本） |
| 作品 | `/works` | 管理作品及权属证明文件 |

## 文件上传规则

文件超过 5MB 自动压缩（图片用 Pillow，PDF 用 Ghostscript）。

| 文件类型 | 命名规则 | 存储目录 |
|---------|---------|---------|
| 代理主体营业执照 | `营业执照_{公司名}.{ext}` | `uploads/营业执照/` |
| 被代理人营业执照 | `营业执照_{被代理人名}.{ext}` | `uploads/被代理人营业执照/` |
| 授权委托书 | `授权委托书_{被代理人名}_截止{YYYYMMDD}.{ext}` | `uploads/授权委托书/` |
| 权属证明 | `权属证明_{作品名}_{uuid8}.{ext}` | `uploads/权属证明/` |
| 其他证明文件 | `其他证明_{作品名}_{序号}_{uuid8}.{ext}` | `uploads/权属证明/` |

更新授权委托书时，旧文件保留在磁盘，新文件以新截止日期命名，历史记录写入 `agent_auth_history` 表。

## 数据库表结构

```
companies          — 代理主体
agents             — 被代理人（关联 companies）
agent_auth_history — 授权委托书变更历史（关联 agents）
works              — 作品（关联 companies + agents）
```

## 常见问题

**Q: 启动后端报数据库连接错误？**  
检查 `.env` 中的 `DB_PASSWORD` 是否正确，数据库是否已创建（`ownership_system`）。

**Q: 前端访问文件提示 404？**  
文件通过 `/api/files/{目录}/{文件名}` 访问，需要登录态。确认 `uploads/` 目录存在且后端有读写权限。

**Q: 上传文件失败，报压缩错误？**  
PDF 压缩依赖 Ghostscript，确认已安装：`gs --version`。图片压缩依赖 Pillow，已在 `requirements.txt` 中。
