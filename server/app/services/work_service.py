"""Work (作品) service layer."""

import json
from datetime import datetime
from sqlalchemy import text

from ..extensions import get_db_session


def list_works(company_id=None, agent_id=None, search_keywords=None):
    with get_db_session() as session:
        conditions = []
        params = {}
        if company_id:
            conditions.append('w.company_id = :company_id')
            params['company_id'] = company_id
        if agent_id:
            conditions.append('w.agent_id = :agent_id')
            params['agent_id'] = agent_id

        # 模糊搜索：按 _ 分隔关键词，OR 关系
        if search_keywords:
            keywords = [kw.strip() for kw in search_keywords.split('_') if kw.strip()]
            if keywords:
                or_parts = []
                for idx, kw in enumerate(keywords):
                    param_name = f'kw{idx}'
                    or_parts.append(f'w.work_name LIKE :{param_name}')
                    params[param_name] = f'%{kw}%'
                conditions.append(f"({' OR '.join(or_parts)})")

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ''
        rows = session.execute(text(f"""
            SELECT w.id, w.company_id, c.company_name, w.agent_id, a.agent_name,
                   w.work_name, w.proof_file, w.other_files,
                   w.created_by, w.created_at, w.updated_at
            FROM works w
            JOIN companies c ON c.id = w.company_id
            JOIN agents a ON a.id = w.agent_id
            {where}
            ORDER BY w.id DESC
        """), params).mappings().all()
    return [_row_to_dict(r) for r in rows]


def get_work(work_id):
    with get_db_session() as session:
        row = session.execute(text("""
            SELECT w.id, w.company_id, c.company_name, w.agent_id, a.agent_name,
                   w.work_name, w.proof_file, w.other_files,
                   w.created_by, w.created_at, w.updated_at
            FROM works w
            JOIN companies c ON c.id = w.company_id
            JOIN agents a ON a.id = w.agent_id
            WHERE w.id = :id
        """), {'id': work_id}).mappings().first()
    return _row_to_dict(row) if row else None


def create_work(company_id, agent_id, work_name, proof_file, other_files, created_by):
    with get_db_session() as session:
        # 检查代理主体和被代理人
        agent = session.execute(text("""
            SELECT id FROM agents WHERE id = :agent_id AND company_id = :company_id
        """), {'agent_id': agent_id, 'company_id': company_id}).first()
        if not agent:
            return None, '被代理人不存在或不属于该代理主体'

        other_json = json.dumps(other_files, ensure_ascii=False) if other_files else None

        session.execute(text("""
            INSERT INTO works (company_id, agent_id, work_name, proof_file, other_files, created_by)
            VALUES (:company_id, :agent_id, :work_name, :proof_file, :other_files, :created_by)
        """), {
            'company_id': company_id,
            'agent_id': agent_id,
            'work_name': work_name.strip(),
            'proof_file': proof_file,
            'other_files': other_json,
            'created_by': created_by,
        })
        work_id = session.execute(text('SELECT LAST_INSERT_ID()')).scalar_one()
        session.commit()

    return get_work(work_id), None


def update_work(work_id, proof_file=None, other_files=None):
    with get_db_session() as session:
        existing = session.execute(text(
            "SELECT id FROM works WHERE id = :id"
        ), {'id': work_id}).first()
        if not existing:
            return None, '作品不存在'

        updates = []
        params = {'id': work_id}
        if proof_file is not None:
            updates.append('proof_file = :proof_file')
            params['proof_file'] = proof_file
        if other_files is not None:
            updates.append('other_files = :other_files')
            params['other_files'] = json.dumps(other_files, ensure_ascii=False) if other_files else None

        if updates:
            sql = f"UPDATE works SET {', '.join(updates)} WHERE id = :id"
            session.execute(text(sql), params)
            session.commit()

    return get_work(work_id), None


def delete_work(work_id):
    with get_db_session() as session:
        result = session.execute(text(
            "DELETE FROM works WHERE id = :id"
        ), {'id': work_id})
        session.commit()
        if result.rowcount == 0:
            return False, '作品不存在'
    return True, None


def _row_to_dict(row):
    other_files = []
    if row['other_files']:
        try:
            other_files = json.loads(row['other_files']) if isinstance(row['other_files'], str) else row['other_files']
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        'id': row['id'],
        'company_id': row['company_id'],
        'company_name': row['company_name'],
        'agent_id': row['agent_id'],
        'agent_name': row['agent_name'],
        'work_name': row['work_name'],
        'proof_file': row['proof_file'],
        'other_files': other_files,
        'created_by': row['created_by'],
        'created_at': row['created_at'].isoformat() if row['created_at'] else None,
        'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
    }
