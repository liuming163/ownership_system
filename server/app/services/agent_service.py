"""Agent (被代理人) service layer."""

from datetime import datetime
from sqlalchemy import text

from ..extensions import get_db_session
from ..utils.validators import normalize_company_name


def list_agents(company_id=None):
    with get_db_session() as session:
        if company_id:
            rows = session.execute(text("""
                SELECT a.id, a.company_id, c.company_name, a.agent_name,
                       a.license_file, a.period_end, a.is_long_term,
                       a.auth_file, a.auth_expires_on, a.created_by, a.created_at, a.updated_at
                FROM agents a
                JOIN companies c ON c.id = a.company_id
                WHERE a.company_id = :company_id
                ORDER BY a.id DESC
            """), {'company_id': company_id}).mappings().all()
        else:
            rows = session.execute(text("""
                SELECT a.id, a.company_id, c.company_name, a.agent_name,
                       a.license_file, a.period_end, a.is_long_term,
                       a.auth_file, a.auth_expires_on, a.created_by, a.created_at, a.updated_at
                FROM agents a
                JOIN companies c ON c.id = a.company_id
                ORDER BY a.id DESC
            """)).mappings().all()
    return [_row_to_dict(r) for r in rows]


def get_agent(agent_id):
    with get_db_session() as session:
        row = session.execute(text("""
            SELECT a.id, a.company_id, c.company_name, a.agent_name,
                   a.license_file, a.period_end, a.is_long_term,
                   a.auth_file, a.auth_expires_on, a.created_by, a.created_at, a.updated_at
            FROM agents a
            JOIN companies c ON c.id = a.company_id
            WHERE a.id = :id
        """), {'id': agent_id}).mappings().first()
    return _row_to_dict(row) if row else None


def create_agent(company_id, agent_name, license_file, period_end, is_long_term,
                 auth_file, auth_expires_on, created_by):
    normalized = normalize_company_name(agent_name)
    with get_db_session() as session:
        # 检查代理主体是否存在
        company = session.execute(text(
            "SELECT 1 FROM companies WHERE id = :id"
        ), {'id': company_id}).first()
        if not company:
            return None, '代理主体不存在'

        # 检查被代理人是否已存在
        exists = session.execute(text("""
            SELECT 1 FROM agents WHERE company_id = :company_id AND agent_name = :name LIMIT 1
        """), {'company_id': company_id, 'name': normalized}).first()
        if exists:
            return None, f'该代理主体下已存在被代理人「{normalized}」'

        session.execute(text("""
            INSERT INTO agents (company_id, agent_name, license_file, period_end, is_long_term,
                               auth_file, auth_expires_on, created_by)
            VALUES (:company_id, :agent_name, :license_file, :period_end, :is_long_term,
                    :auth_file, :auth_expires_on, :created_by)
        """), {
            'company_id': company_id,
            'agent_name': normalized,
            'license_file': license_file,
            'period_end': period_end if not is_long_term else None,
            'is_long_term': 1 if is_long_term else 0,
            'auth_file': auth_file,
            'auth_expires_on': auth_expires_on,
            'created_by': created_by,
        })
        agent_id = session.execute(text('SELECT LAST_INSERT_ID()')).scalar_one()

        # 同时记录到历史表
        session.execute(text("""
            INSERT INTO agent_auth_history (agent_id, auth_file, auth_expires_on, uploaded_by)
            VALUES (:agent_id, :auth_file, :auth_expires_on, :uploaded_by)
        """), {
            'agent_id': agent_id,
            'auth_file': auth_file,
            'auth_expires_on': auth_expires_on,
            'uploaded_by': created_by,
        })
        session.commit()

    return get_agent(agent_id), None


def update_agent_auth(agent_id, auth_file, auth_expires_on, uploaded_by):
    """更新授权委托书，旧记录保留到历史表。"""
    with get_db_session() as session:
        existing = session.execute(text(
            "SELECT id FROM agents WHERE id = :id"
        ), {'id': agent_id}).first()
        if not existing:
            return None, '被代理人不存在'

        # 更新 agents 表的当前授权
        session.execute(text("""
            UPDATE agents
            SET auth_file = :auth_file, auth_expires_on = :auth_expires_on
            WHERE id = :id
        """), {'auth_file': auth_file, 'auth_expires_on': auth_expires_on, 'id': agent_id})

        # 追加历史记录
        session.execute(text("""
            INSERT INTO agent_auth_history (agent_id, auth_file, auth_expires_on, uploaded_by)
            VALUES (:agent_id, :auth_file, :auth_expires_on, :uploaded_by)
        """), {
            'agent_id': agent_id,
            'auth_file': auth_file,
            'auth_expires_on': auth_expires_on,
            'uploaded_by': uploaded_by,
        })
        session.commit()

    return get_agent(agent_id), None


def get_auth_history(agent_id):
    """获取授权委托书变更历史。"""
    with get_db_session() as session:
        rows = session.execute(text("""
            SELECT id, auth_file, auth_expires_on, replaced_at, uploaded_by
            FROM agent_auth_history
            WHERE agent_id = :agent_id
            ORDER BY replaced_at DESC
        """), {'agent_id': agent_id}).mappings().all()
    return [{
        'id': r['id'],
        'auth_file': r['auth_file'],
        'auth_expires_on': r['auth_expires_on'].isoformat() if r['auth_expires_on'] else None,
        'replaced_at': r['replaced_at'].isoformat() if r['replaced_at'] else None,
        'uploaded_by': r['uploaded_by'],
    } for r in rows]


def delete_agent(agent_id):
    with get_db_session() as session:
        has_works = session.execute(text(
            "SELECT 1 FROM works WHERE agent_id = :id LIMIT 1"
        ), {'id': agent_id}).first()
        if has_works:
            return False, '该被代理人下存在作品，无法删除'

        # 先删历史
        session.execute(text(
            "DELETE FROM agent_auth_history WHERE agent_id = :id"
        ), {'id': agent_id})
        result = session.execute(text(
            "DELETE FROM agents WHERE id = :id"
        ), {'id': agent_id})
        session.commit()
        if result.rowcount == 0:
            return False, '被代理人不存在'

    return True, None


def _row_to_dict(row):
    return {
        'id': row['id'],
        'company_id': row['company_id'],
        'company_name': row['company_name'],
        'agent_name': row['agent_name'],
        'license_file': row['license_file'],
        'period_end': row['period_end'].isoformat() if row['period_end'] else None,
        'is_long_term': bool(row['is_long_term']),
        'auth_file': row['auth_file'],
        'auth_expires_on': row['auth_expires_on'].isoformat() if row['auth_expires_on'] else None,
        'created_by': row['created_by'],
        'created_at': row['created_at'].isoformat() if row['created_at'] else None,
        'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
    }
