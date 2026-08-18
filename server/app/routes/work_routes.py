"""Work (作品) routes."""

from flask import Blueprint, request, send_file
from datetime import datetime
from urllib.parse import quote
import zipfile
import os
import tempfile

from ..auth.decorators import login_required, get_current_user
from ..services import work_service, file_service
from ..utils.response import success, error
from ..utils.validators import sanitize_filename_part
from ..config import Config

work_bp = Blueprint('works', __name__, url_prefix='/api/works')


@work_bp.route('', methods=['GET'])
@login_required
def list_works():
    company_id = request.args.get('company_id', type=int)
    agent_id = request.args.get('agent_id', type=int)
    search_keywords = request.args.get('search', '').strip()
    data = work_service.list_works(company_id, agent_id, search_keywords)
    return success(data)


@work_bp.route('/<int:work_id>', methods=['GET'])
@login_required
def get_work(work_id):
    data = work_service.get_work(work_id)
    if not data:
        return error('作品不存在', 404)
    return success(data)


@work_bp.route('', methods=['POST'])
@login_required
def create_work():
    company_id = request.form.get('company_id', type=int)
    agent_id = request.form.get('agent_id', type=int)
    work_name = request.form.get('work_name', '').strip()
    proof_file = request.files.get('proof_file')
    other_files = request.files.getlist('other_files')

    if not company_id or not agent_id:
        return error('请选择代理主体和被代理人')
    if not work_name:
        return error('作品名称不能为空')
    if not proof_file or not proof_file.filename:
        return error('请上传权属证明文件')

    safe_work_name = sanitize_filename_part(work_name)

    # 保存权属证明
    proof_filename = file_service.save_proof_file(proof_file, safe_work_name)

    # 保存其他证明
    other_filenames = []
    for idx, f in enumerate([f for f in other_files if f and f.filename], start=1):
        fname = file_service.save_other_proof_file(f, safe_work_name, idx)
        other_filenames.append(fname)

    data, err = work_service.create_work(
        company_id=company_id,
        agent_id=agent_id,
        work_name=work_name,
        proof_file=proof_filename,
        other_files=other_filenames if other_filenames else None,
        created_by=get_current_user(),
    )
    if err:
        return error(err)
    return success(data)


@work_bp.route('/<int:work_id>', methods=['PUT'])
@login_required
def update_work(work_id):
    proof_file = request.files.get('proof_file')
    other_files = request.files.getlist('other_files')

    existing = work_service.get_work(work_id)
    if not existing:
        return error('作品不存在', 404)

    safe_work_name = sanitize_filename_part(existing['work_name'])

    new_proof = None
    if proof_file and proof_file.filename:
        new_proof = file_service.save_proof_file(proof_file, safe_work_name)

    new_others = None
    valid_others = [f for f in other_files if f and f.filename]
    if valid_others:
        new_others = existing.get('other_files', []) or []
        for idx, f in enumerate(valid_others, start=len(new_others) + 1):
            fname = file_service.save_other_proof_file(f, safe_work_name, idx)
            new_others.append(fname)

    data, err = work_service.update_work(work_id, proof_file=new_proof, other_files=new_others)
    if err:
        return error(err)
    return success(data)


@work_bp.route('/<int:work_id>', methods=['DELETE'])
@login_required
def delete_work(work_id):
    ok, err = work_service.delete_work(work_id)
    if not ok:
        return error(err)
    return success(message='删除成功')


@work_bp.route('/package', methods=['POST'])
@login_required
def package_works():
    data = request.get_json()
    work_ids = data.get('work_ids', [])

    if not work_ids:
        return error('请选择要打包的作品')

    # 查询所有作品
    works = []
    for work_id in work_ids:
        work = work_service.get_work(work_id)
        if work:
            works.append(work)

    if not works:
        return error('未找到有效的作品')

    # 创建临时zip文件
    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    temp_zip.close()

    try:
        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for work in works:
                work_name = sanitize_filename_part(work['work_name'])
                work_folder = f"{work_name}/"

                # 添加权属证明
                if work.get('proof_file'):
                    proof_path = os.path.join(Config.UPLOAD_FOLDER, '权属证明', work['proof_file'])
                    if os.path.exists(proof_path):
                        zipf.write(proof_path, f"{work_folder}权属证明_{work['proof_file']}")

                # 添加其他证明
                other_files = work.get('other_files', []) or []
                for idx, filename in enumerate(other_files, 1):
                    other_path = os.path.join(Config.UPLOAD_FOLDER, '权属证明', filename)
                    if os.path.exists(other_path):
                        zipf.write(other_path, f"{work_folder}其他证明{idx}_{filename}")

        # 生成文件名
        today = datetime.now().strftime('%Y%m%d')
        zip_filename = f"作品打包_共{len(works)}部_{today}.zip"

        response = send_file(
            temp_zip.name,
            as_attachment=True,
            mimetype='application/zip'
        )

        # 手动设置 Content-Disposition 响应头，支持中文文件名
        encoded_filename = quote(zip_filename)
        response.headers['Content-Disposition'] = f'attachment; filename="{encoded_filename}"'

        # 响应发送后删除临时文件
        @response.call_on_close
        def cleanup():
            try:
                os.unlink(temp_zip.name)
            except:
                pass

        return response
    except Exception as e:
        # 出错时立即删除临时文件
        try:
            os.unlink(temp_zip.name)
        except:
            pass
        return error(f'打包失败: {str(e)}')

