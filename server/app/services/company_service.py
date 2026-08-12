"""Company (代理主体) service layer."""

from datetime import datetime
from sqlalchemy import text

from ..extensions import get_db_session
from ..utils.validators import normalize_company_name


def list_companies():
    with get_db_session() as session:
        rows = session.execute(text("""
            SELECT id, company_name, license_file, period_end, is_long_term,
                   created_by, created_at, updated_at
            FROM companies
            ORDER BY id DESC
        """)).mappings().all()
    return [_row_to_dict(r) for r in rows]


def get_company(company_id):
    with get_db_session() as session:
        row = session.execute(text("""
            SELECT id, company_name, license_file, period_end, is_long_term,
                   created_by, created_at, updated_at
            FROM companies WHERE id = :id
        """), {'id': company_id}).mappings().first()
    return _row_to_dict(row) if row else None


def create_company(company_name, license_file, period_end, is_long_term, created_by):
    normalized = normalize_company_name(company_name)
    with get_db_session() as session:
        exists = session.execute(text(
            "SELECT 1 FROM companies WHERE company_name = :name LIMIT 1"
        ), {'name': normalized}).first()
        if exists:
            return None, f'代理主体「{normalized}」已存在'

        session.execute(text("""
            INSERT INTO companies (company_name, license_file, period_end, is_long_term, created_by)
            VALUES (:company_name, :license_file, :period_end, :is_long_term, :created_by)
        """), {
            'company_name': normalized,
            'license_file': license_file,
            'period_end': period_end if not is_long_term else None,
            'is_long_term': 1 if is_long_term else 0,
            'created_by': created_by,
        })
        company_id = session.execute(text('SELECT LAST_INSERT_ID()')).scalar_one()
        session.commit()

    return get_company(company_id), None


def update_company(company_id, license_file=None, period_end=None, is_long_term=None):
    with get_db_session() as session:
        existing = session.execute(text(
            "SELECT id FROM companies WHERE id = :id"
        ), {'id': company_id}).first()
        if not existing:
            return None, '代理主体不存在'

        updates = []
        params = {'id': company_id}

        if license_file is not None:
            updates.append('license_file = :license_file')
            params['license_file'] = license_file
        if is_long_term is not None:
            updates.append('is_long_term = :is_long_term')
            params['is_long_term'] = 1 if is_long_term else 0
            if is_long_term:
                updates.append('period_end = NULL')
            elif period_end is not None:
                updates.append('period_end = :period_end')
                params['period_end'] = period_end
        elif period_end is not None:
            updates.append('period_end = :period_end')
            params['period_end'] = period_end

        if updates:
            sql = f"UPDATE companies SET {', '.join(updates)} WHERE id = :id"
            session.execute(text(sql), params)
            session.commit()

    return get_company(company_id), None


def delete_company(company_id):
    with get_db_session() as session:
        has_agents = session.execute(text(
            "SELECT 1 FROM agents WHERE company_id = :id LIMIT 1"
        ), {'id': company_id}).first()
        if has_agents:
            return False, '该代理主体下存在被代理人，无法删除'

        result = session.execute(text(
            "DELETE FROM companies WHERE id = :id"
        ), {'id': company_id})
        session.commit()
        if result.rowcount == 0:
            return False, '代理主体不存在'

    return True, None


def _row_to_dict(row):
    return {
        'id': row['id'],
        'company_name': row['company_name'],
        'license_file': row['license_file'],
        'period_end': row['period_end'].isoformat() if row['period_end'] else None,
        'is_long_term': bool(row['is_long_term']),
        'created_by': row['created_by'],
        'created_at': row['created_at'].isoformat() if row['created_at'] else None,
        'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
    }
