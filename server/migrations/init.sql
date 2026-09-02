CREATE DATABASE IF NOT EXISTS ownership_system
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;

USE ownership_system;

-- 代理主体
CREATE TABLE companies (
    id           INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    company_name VARCHAR(255) NOT NULL COMMENT '公司名称',
    license_file VARCHAR(500) NOT NULL COMMENT '营业执照文件名',
    period_end   DATE         NULL     COMMENT '营业期限截止日期，NULL表示长期',
    is_long_term TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '1=长期',
    created_by   VARCHAR(100) COMMENT '创建人用户名',
    created_at   DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at   DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_company_name (company_name)
) ENGINE=InnoDB COMMENT '代理主体';

-- 被代理人
CREATE TABLE agents (
    id              INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    company_id      INT          NOT NULL COMMENT '所属代理主体',
    agent_name      VARCHAR(255) NOT NULL COMMENT '被代理人名称',
    license_file    VARCHAR(500) NOT NULL COMMENT '被代理人营业执照文件名',
    period_end      DATE         NULL     COMMENT '营业期限截止，NULL表示长期',
    is_long_term    TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '1=长期',
    auth_file       VARCHAR(500) NOT NULL COMMENT '当前生效的授权委托书文件名',
    auth_expires_on DATE         NOT NULL COMMENT '授权截止日期',
    created_by      VARCHAR(100) COMMENT '创建人用户名',
    created_at      DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at      DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_company_agent (company_id, agent_name),
    FOREIGN KEY (company_id) REFERENCES companies(id)
) ENGINE=InnoDB COMMENT '被代理人';

-- 授权委托书变更历史
CREATE TABLE agent_auth_history (
    id              INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    agent_id        INT          NOT NULL COMMENT '被代理人ID',
    auth_file       VARCHAR(500) NOT NULL COMMENT '授权委托书文件名',
    auth_expires_on DATE         NOT NULL COMMENT '此版本的截止日期',
    replaced_at     DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
    uploaded_by     VARCHAR(100) COMMENT '上传人',
    FOREIGN KEY (agent_id) REFERENCES agents(id)
) ENGINE=InnoDB COMMENT '授权委托书变更历史';

-- 作品
CREATE TABLE works (
    id           INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    company_id   INT          NOT NULL COMMENT '代理主体',
    agent_id     INT          NOT NULL COMMENT '被代理人',
    work_name    VARCHAR(255) NOT NULL COMMENT '作品名称',
    alias        VARCHAR(255) NULL     COMMENT '作品别名（可选）',
    proof_file   VARCHAR(500) NOT NULL COMMENT '权属证明文件名',
    other_files  JSON         NULL     COMMENT '其他证明文件列表',
    created_by   VARCHAR(100) COMMENT '创建人',
    created_at   DATETIME     DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_by   VARCHAR(100) COMMENT '最近更新人',
    updated_at   DATETIME     NULL COMMENT '最近更新时间',
    FOREIGN KEY (company_id) REFERENCES companies(id),
    FOREIGN KEY (agent_id)   REFERENCES agents(id)
) ENGINE=InnoDB COMMENT '作品';
