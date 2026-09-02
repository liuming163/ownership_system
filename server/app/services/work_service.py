"""Work (作品) service layer."""

import json
from datetime import datetime
from sqlalchemy import text

from ..extensions import get_db_session


def _serialize_for_compare(value):
    """把 other_files 规范化成可比较的 JSON 字符串（顺序无关）。"""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value  # 解析失败时退化为字符串比较
    if isinstance(value, list):
        return json.dumps(sorted(value), ensure_ascii=False)
    return str(value)


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
        # 同时搜索作品名称和别名（别名也按 _ 拆分）
        if search_keywords:
            keywords = [kw.strip() for kw in search_keywords.split('_') if kw.strip()]
            if keywords:
                or_parts = []
                for idx, kw in enumerate(keywords):
                    param_name = f'kw{idx}'
                    # 搜索作品名称或别名中包含该关键词
                    or_parts.append(f'(w.work_name LIKE :{param_name} OR w.alias LIKE :{param_name})')
                    params[param_name] = f'%{kw}%'
                conditions.append(f"({' OR '.join(or_parts)})")

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ''
        rows = session.execute(text(f"""
            SELECT w.id, w.company_id, c.company_name, w.agent_id, a.agent_name,
                   w.work_name, w.alias, w.proof_file, w.other_files,
                   w.created_by, w.created_at, w.updated_by, w.updated_at
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
                   w.work_name, w.alias, w.proof_file, w.other_files,
                   w.created_by, w.created_at, w.updated_by, w.updated_at
            FROM works w
            JOIN companies c ON c.id = w.company_id
            JOIN agents a ON a.id = w.agent_id
            WHERE w.id = :id
        """), {'id': work_id}).mappings().first()
    return _row_to_dict(row) if row else None


def create_work(company_id, agent_id, work_name, alias, proof_file, other_files, created_by):
    with get_db_session() as session:
        # 检查代理主体和被代理人
        agent = session.execute(text("""
            SELECT id FROM agents WHERE id = :agent_id AND company_id = :company_id
        """), {'agent_id': agent_id, 'company_id': company_id}).first()
        if not agent:
            return None, '被代理人不存在或不属于该代理主体'

        other_json = json.dumps(other_files, ensure_ascii=False) if other_files else None
        now = datetime.now()

        session.execute(text("""
            INSERT INTO works (company_id, agent_id, work_name, alias, proof_file, other_files, created_by, created_at, updated_by, updated_at)
            VALUES (:company_id, :agent_id, :work_name, :alias, :proof_file, :other_files, :created_by, :created_at, :updated_by, :updated_at)
        """), {
            'company_id': company_id,
            'agent_id': agent_id,
            'work_name': work_name.strip(),
            'alias': alias.strip() if alias else '',
            'proof_file': proof_file,
            'other_files': other_json,
            'created_by': created_by,
            'created_at': now,
            'updated_by': created_by,
            'updated_at': now,
        })
        work_id = session.execute(text('SELECT LAST_INSERT_ID()')).scalar_one()

        # 写入历史：记录本次上传的 proof_file / other_files（首个版本）
        session.execute(text("""
            INSERT INTO works_history (work_id, work_name, proof_file, other_files, replaced_at, uploaded_by)
            VALUES (:work_id, :work_name, :proof_file, :other_files, :replaced_at, :uploaded_by)
        """), {
            'work_id': work_id,
            'work_name': work_name.strip(),
            'proof_file': proof_file,
            'other_files': other_json,
            'replaced_at': now,
            'uploaded_by': created_by,
        })

        session.commit()

    return get_work(work_id), None


def update_work(work_id, alias=None, proof_file=None, other_files=None, updated_by=None):
    with get_db_session() as session:
        existing = session.execute(text(
            "SELECT id, work_name, proof_file, other_files FROM works WHERE id = :id"
        ), {'id': work_id}).mappings().first()
        if not existing:
            return None, '作品不存在'

        old_proof_file = existing['proof_file']
        old_other_files = json.loads(existing['other_files']) if existing['other_files'] else []
        if not isinstance(old_other_files, list):
            old_other_files = []

        # 检测文件是否真的变了
        new_other_json = json.dumps(other_files, ensure_ascii=False) if other_files else None
        proof_changed = proof_file is not None and proof_file != old_proof_file
        others_changed = (
            (other_files is None and old_other_files)
            or (other_files is not None and _serialize_for_compare(other_files) != _serialize_for_compare(old_other_files))
        )

        updates = []
        params = {'id': work_id}

        if alias is not None:
            updates.append('alias = :alias')
            params['alias'] = alias.strip() if alias else None

        if proof_file is not None:
            updates.append('proof_file = :proof_file')
            params['proof_file'] = proof_file

        if other_files is not None:
            updates.append('other_files = :other_files')
            params['other_files'] = new_other_json

        if updates:
            now = datetime.now()
            updates.append('updated_by = :updated_by')
            updates.append('updated_at = :updated_at')
            params['updated_by'] = updated_by
            params['updated_at'] = now

            sql = f"UPDATE works SET {', '.join(updates)} WHERE id = :id"
            session.execute(text(sql), params)

            # 仅在 proof_file / other_files 真变了时才写入历史
            # 历史记录保存"本次上传后的完整文件状态"（参照 agent_auth_history 的设计）
            if proof_changed or others_changed:
                session.execute(text("""
                    INSERT INTO works_history (work_id, work_name, proof_file, other_files, replaced_at, uploaded_by)
                    VALUES (:work_id, :work_name, :proof_file, :other_files, :replaced_at, :uploaded_by)
                """), {
                    'work_id': work_id,
                    'work_name': existing['work_name'],
                    'proof_file': (proof_file if proof_changed else old_proof_file) or None,
                    'other_files': (new_other_json if others_changed else (json.dumps(old_other_files, ensure_ascii=False) if old_other_files else None)),
                    'replaced_at': now,
                    'uploaded_by': updated_by,
                })

            session.commit()

    # 注意：旧文件保留在磁盘上（"永久追溯"业务诉求）
    return get_work(work_id), None


def delete_work(work_id):
    with get_db_session() as session:
        existing = session.execute(text(
            "SELECT id FROM works WHERE id = :id"
        ), {'id': work_id}).first()
        if not existing:
            return False, '作品不存在'

        # 删除 works 记录；works_history 与磁盘文件均保留（业务诉求：永久追溯）
        session.execute(text("DELETE FROM works WHERE id = :id"), {'id': work_id})
        session.commit()

    return True, None


def get_work_history(work_id):
    with get_db_session() as session:
        rows = session.execute(text("""
            SELECT id, work_id, work_name, proof_file, other_files, replaced_at, uploaded_by
            FROM works_history
            WHERE work_id = :work_id
            ORDER BY replaced_at DESC, id DESC
        """), {'work_id': work_id}).mappings().all()
    return [_history_row_to_dict(r) for r in rows]


def _history_row_to_dict(row):
    other_files = []
    if row['other_files']:
        try:
            other_files = json.loads(row['other_files']) if isinstance(row['other_files'], str) else row['other_files']
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        'id': row['id'],
        'work_id': row['work_id'],
        'work_name': row['work_name'],
        'proof_file': row['proof_file'],
        'other_files': other_files,
        'replaced_at': row['replaced_at'].isoformat() if row['replaced_at'] else None,
        'uploaded_by': row['uploaded_by'],
    }


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
        'alias': row['alias'],
        'proof_file': row['proof_file'],
        'other_files': other_files,
        'created_by': row['created_by'],
        'created_at': row['created_at'].isoformat() if row['created_at'] else None,
        'updated_by': row.get('updated_by'),
        'updated_at': row['updated_at'].isoformat() if row.get('updated_at') else None,
    }
