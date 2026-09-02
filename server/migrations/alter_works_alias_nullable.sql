-- 把 works.alias 改为 NULL，让"别名不填"语义正确（与 init.sql 对齐）
-- 现有数据中 alias = '' (空串) 也规范化为 NULL
-- 用法：mysql -h <host> -u <user> -p ownership_system < alter_works_alias_nullable.sql
-- 或者在 Python 里用 pymysql 直接执行（参考 deploy 时用的 init_db.py）

USE ownership_system;

-- 1. 规范化已有数据：空串 → NULL
UPDATE works SET alias = NULL WHERE alias = '';

-- 2. 修改字段允许 NULL
ALTER TABLE works MODIFY COLUMN alias VARCHAR(255) NULL COMMENT '作品别名（可选）';