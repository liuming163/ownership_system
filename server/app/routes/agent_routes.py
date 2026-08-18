"""Agent (被代理人) routes."""

from flask import Blueprint, request
from datetime import datetime

from ..auth.decorators import login_required, get_current_user
from ..utils.response import success, error
from ..services import agent_service, file_service, company_service
from ..utils.validators import normalize_company_name, sanitize_filename_part

agent_bp = Blueprint('agent', __name__, url_prefix='/api/agents')


@agent_bp.route('', methods=['GET'])
@login_required
def list_agents():
    """获取被代理人列表（可按 company_id 过滤）"""
    company_id = request.args.get('company_id', type=int)
    return success(agent_service.list_agents(company_id))


@agent_bp.route('/expiring-auth', methods=['GET'])
@login_required
def get_expiring_auth():
    """获取授权过期和即将过期的被代理人列表"""
    expired, expiring_soon = agent_service.get_expiring_auth()
    return success({
        'expired': expired,
        'expiring_soon': expiring_soon
    })


@agent_bp.route('/<int:agent_id>', methods=['GET'])
@login_required
def get_agent(agent_id):
    """获取被代理人详情"""
    data = agent_service.get_agent(agent_id)
    if not data:
        return error('被代理人不存在', 404)
    return success(data)


@agent_bp.route('', methods=['POST'])
@login_required
def create_agent():
    """创建被代理人，上传营业执照和授权委托书。"""
    company_id = request.form.get('company_id', type=int)
    agent_name = request.form.get('agent_name', '').strip()
    license_file = request.files.get('license_file')
    period_end = request.form.get('period_end', '').strip()
    is_long_term = request.form.get('is_long_term') == 'true'
    auth_file = request.files.get('auth_file')
    auth_expires_on = request.form.get('auth_expires_on', '').strip()

    if not company_id:
        return error('请选择代理主体')
    if not agent_name:
        return error('被代理人名称不能为空')
    if not license_file or not license_file.filename:
        return error('请上传被代理人营业执照')
    if not auth_file or not auth_file.filename:
        return error('请上传授权委托书')
    if not auth_expires_on:
        return error('请填写授权期限截止日期')
    if not is_long_term and not period_end:
        return error('请填写营业期限截止日期或选择长期')

    # 获取代理主体名称
    from app.services import company_service
    company = company_service.get_company(company_id)
    if not company:
        return error('代理主体不存在')

    safe_name = sanitize_filename_part(normalize_company_name(agent_name))
    safe_company_name = sanitize_filename_part(normalize_company_name(company['company_name']))

    # 保存文件
    license_filename = file_service.save_agent_license(license_file, safe_name)
    auth_filename = file_service.save_auth_file(auth_file, safe_name, safe_company_name, auth_expires_on)

    data, err = agent_service.create_agent(
        company_id=company_id,
        agent_name=agent_name,
        license_file=license_filename,
        period_end=period_end,
        is_long_term=is_long_term,
        auth_file=auth_filename,
        auth_expires_on=auth_expires_on,
        created_by=get_current_user(),
    )
    if err:
        return error(err)
    return success(data)


@agent_bp.route('/<int:agent_id>/auth', methods=['PUT'])
@login_required
def update_auth(agent_id):
    """更新授权委托书（不覆盖旧文件）。"""
    auth_file = request.files.get('auth_file')
    auth_expires_on = request.form.get('auth_expires_on', '').strip()

    if not auth_file or not auth_file.filename:
        return error('请上传授权委托书')
    if not auth_expires_on:
        return error('请填写授权期限截止日期')

    existing = agent_service.get_agent(agent_id)
    if not existing:
        return error('被代理人不存在', 404)

    safe_name = sanitize_filename_part(normalize_company_name(existing['agent_name']))
    safe_company_name = sanitize_filename_part(normalize_company_name(existing['company_name']))
    auth_filename = file_service.save_auth_file(auth_file, safe_name, safe_company_name, auth_expires_on)

    data, err = agent_service.update_agent_auth(
        agent_id=agent_id,
        auth_file=auth_filename,
        auth_expires_on=auth_expires_on,
        uploaded_by=get_current_user(),
    )
    if err:
        return error(err)
    return success(data)


@agent_bp.route('/<int:agent_id>/auth/history', methods=['GET'])
@login_required
def get_auth_history(agent_id):
    """获取被代理人的授权委托书历史记录。"""
    history = agent_service.get_agent_auth_history(agent_id)
    return success(history)


@agent_bp.route('/<int:agent_id>', methods=['DELETE'])
@login_required
def delete_agent(agent_id):
    """删除被代理人，同时删除数据库记录和本地文件。"""
    err = agent_service.delete_agent(agent_id)
    if err:
        return error(err)
    return success(message='删除成功')

