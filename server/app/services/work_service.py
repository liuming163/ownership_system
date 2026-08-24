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
            'alias': alias.strip() if alias else None,
            'proof_file': proof_file,
            'other_files': other_json,
            'created_by': created_by,
            'created_at': now,
            'updated_by': created_by,
            'updated_at': now,
        })
        work_id = session.execute(text('SELECT LAST_INSERT_ID()')).scalar_one()
        session.commit()

    return get_work(work_id), None


def update_work(work_id, alias=None, proof_file=None, other_files=None, updated_by=None):
    import os
    from flask import current_app

    with get_db_session() as session:
        existing = session.execute(text(
            "SELECT id, proof_file, other_files FROM works WHERE id = :id"
        ), {'id': work_id}).mappings().first()
        if not existing:
            return None, '作品不存在'

        # 需要删除的旧文件列表
        old_proof_file = existing['proof_file']
        old_other_files = []
        if existing['other_files']:
            try:
                old_other_files = json.loads(existing['other_files']) if isinstance(existing['other_files'], str) else existing['other_files']
            except (json.JSONDecodeError, TypeError):
                pass

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
            params['other_files'] = json.dumps(other_files, ensure_ascii=False) if other_files else None

        if updates:
            updates.append('updated_by = :updated_by')
            updates.append('updated_at = :updated_at')
            params['updated_by'] = updated_by
            params['updated_at'] = datetime.now()

            sql = f"UPDATE works SET {', '.join(updates)} WHERE id = :id"
            session.execute(text(sql), params)
            session.commit()

    # 删除旧文件（在数据库提交成功后）
    upload_base = current_app.config['UPLOAD_FOLDER']
    proof_dir = os.path.join(upload_base, '权属证明')

    # 1. 如果上传了新的权属证明，删除旧的权属证明文件
    if proof_file is not None and old_proof_file:
        old_proof_path = os.path.join(proof_dir, old_proof_file)
        if os.path.exists(old_proof_path):
            try:
                os.remove(old_proof_path)
            except OSError:
                pass  # 删除失败不影响业务

    # 2. 如果上传了新的其他证明，删除旧的其他证明文件
    if other_files is not None and old_other_files:
        for filename in old_other_files:
            old_other_path = os.path.join(proof_dir, filename)
            if os.path.exists(old_other_path):
                try:
                    os.remove(old_other_path)
                except OSError:
                    pass  # 删除失败不影响业务

    return get_work(work_id), None


def delete_work(work_id):
    from . import file_service
    import os
    from flask import current_app

    with get_db_session() as session:
        # 获取作品信息（用于删除文件）
        work = session.execute(text("""
            SELECT work_name, proof_file, other_files
            FROM works WHERE id = :id
        """), {'id': work_id}).mappings().first()

        if not work:
            return False, '作品不存在'

        # 删除数据库记录
        result = session.execute(text(
            "DELETE FROM works WHERE id = :id"
        ), {'id': work_id})
        session.commit()

        if result.rowcount == 0:
            return False, '作品不存在'

    # 删除本地文件
    upload_base = current_app.config['UPLOAD_FOLDER']
    proof_dir = os.path.join(upload_base, '权属证明')

    # 1. 删除权属证明文件
    if work['proof_file']:
        proof_path = os.path.join(proof_dir, work['proof_file'])
        if os.path.exists(proof_path):
            try:
                os.remove(proof_path)
            except OSError:
                pass

    # 2. 删除其他证明文件
    if work['other_files']:
        try:
            other_files = json.loads(work['other_files']) if isinstance(work['other_files'], str) else work['other_files']
            for filename in other_files:
                other_path = os.path.join(proof_dir, filename)
                if os.path.exists(other_path):
                    try:
                        os.remove(other_path)
                    except OSError:
                        pass
        except (json.JSONDecodeError, TypeError):
            pass

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
        'alias': row['alias'],
        'proof_file': row['proof_file'],
        'other_files': other_files,
        'created_by': row['created_by'],
        'created_at': row['created_at'].isoformat() if row['created_at'] else None,
        'updated_by': row.get('updated_by'),
        'updated_at': row['updated_at'].isoformat() if row.get('updated_at') else None,
    }
