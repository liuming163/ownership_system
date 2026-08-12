"""Company routes."""

from flask import Blueprint, request

from ..auth.decorators import login_required, get_current_user
from ..services import company_service, file_service
from ..utils.response import success, error
from ..utils.validators import normalize_company_name, sanitize_filename_part

company_bp = Blueprint('companies', __name__, url_prefix='/api/companies')


@company_bp.route('', methods=['GET'])
@login_required
def list_companies():
    data = company_service.list_companies()
    return success(data)


@company_bp.route('/<int:company_id>', methods=['GET'])
@login_required
def get_company(company_id):
    data = company_service.get_company(company_id)
    if not data:
        return error('代理主体不存在', 404)
    return success(data)


@company_bp.route('', methods=['POST'])
@login_required
def create_company():
    company_name = request.form.get('company_name', '').strip()
    period_end = request.form.get('period_end', '').strip() or None
    is_long_term = request.form.get('is_long_term', '0') == '1'
    license_file = request.files.get('license_file')

    if not company_name:
        return error('公司名称不能为空')
    if not license_file or not license_file.filename:
        return error('请上传营业执照')
    if not is_long_term and not period_end:
        return error('请填写营业期限截止日期或选择长期')

    # 保存文件
    safe_name = sanitize_filename_part(normalize_company_name(company_name))
    filename = file_service.save_company_license(license_file, safe_name)

    data, err = company_service.create_company(
        company_name=company_name,
        license_file=filename,
        period_end=period_end,
        is_long_term=is_long_term,
        created_by=get_current_user(),
    )
    if err:
        return error(err)
    return success(data)


@company_bp.route('/<int:company_id>', methods=['PUT'])
@login_required
def update_company(company_id):
    period_end = request.form.get('period_end', '').strip() or None
    is_long_term = request.form.get('is_long_term', '0') == '1'
    license_file = request.files.get('license_file')

    new_license = None
    if license_file and license_file.filename:
        existing = company_service.get_company(company_id)
        if not existing:
            return error('代理主体不存在', 404)
        safe_name = sanitize_filename_part(normalize_company_name(existing['company_name']))
        new_license = file_service.save_company_license(license_file, safe_name)

    data, err = company_service.update_company(
        company_id,
        license_file=new_license,
        period_end=period_end,
        is_long_term=is_long_term,
    )
    if err:
        return error(err)
    return success(data)


@company_bp.route('/<int:company_id>', methods=['DELETE'])
@login_required
def delete_company(company_id):
    ok, err = company_service.delete_company(company_id)
    if not ok:
        return error(err)
    return success(message='删除成功')
