<template>
  <div class="page-container">
    <div class="page-header">
      <h3>代理主体管理</h3>
      <el-button type="primary" @click="showAddDialog">新增代理主体</el-button>
    </div>

    <el-table :data="companies" v-loading="loading" border stripe>
      <el-table-column prop="company_name" label="公司名称" min-width="200" />
      <el-table-column label="营业执照" width="100" align="center">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="viewFile('营业执照', row.license_file)">
            查看
          </el-button>
        </template>
      </el-table-column>
      <el-table-column label="营业期限" width="150">
        <template #default="{ row }">
          {{ row.is_long_term ? '长期' : row.period_end || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="created_by" label="创建人" width="120" />
      <el-table-column prop="created_at" label="创建时间" width="180" />
      <el-table-column label="操作" width="150" align="center">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="showEditDialog(row)">编辑</el-button>
          <el-popconfirm v-if="userStore.canDelete" title="确定删除该代理主体？" @confirm="handleDelete(row.id)">
            <template #reference>
              <el-button type="danger" link size="small">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新增/编辑弹窗 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑代理主体' : '新增代理主体'" width="500px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-form-item label="公司名称" prop="company_name">
          <el-input v-model="form.company_name" :disabled="isEdit" placeholder="请输入公司名称" />
        </el-form-item>
        <el-form-item label="营业执照" prop="license_file">
          <el-upload
            :auto-upload="false"
            :limit="1"
            :on-change="handleFileChange"
            :file-list="fileList"
            accept=".jpg,.jpeg,.png,.pdf"
          >
            <el-button size="small" type="primary">选择文件</el-button>
          </el-upload>
        </el-form-item>
        <el-form-item label="营业期限">
          <el-checkbox v-model="form.is_long_term">长期</el-checkbox>
          <el-date-picker
            v-if="!form.is_long_term"
            v-model="form.period_end"
            type="date"
            placeholder="截止日期"
            value-format="YYYY-MM-DD"
            style="margin-left: 12px"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getCompanies, createCompany, updateCompany, deleteCompany } from '../api/company'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()

const companies = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const submitting = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const formRef = ref()
const fileList = ref([])
let selectedFile = null

const form = reactive({
  company_name: '',
  is_long_term: false,
  period_end: '',
})

const rules = {
  company_name: [{ required: true, message: '请输入公司名称', trigger: 'blur' }],
}

onMounted(() => loadData())

async function loadData() {
  loading.value = true
  try {
    const res = await getCompanies()
    if (res.success) companies.value = res.data
  } finally {
    loading.value = false
  }
}

function showAddDialog() {
  isEdit.value = false
  editId.value = null
  form.company_name = ''
  form.is_long_term = false
  form.period_end = ''
  fileList.value = []
  selectedFile = null
  dialogVisible.value = true
}

function showEditDialog(row) {
  isEdit.value = true
  editId.value = row.id
  form.company_name = row.company_name
  form.is_long_term = row.is_long_term
  form.period_end = row.period_end || ''
  fileList.value = []
  selectedFile = null
  dialogVisible.value = true
}

function handleFileChange(file) {
  selectedFile = file.raw
}

async function handleSubmit() {
  await formRef.value.validate()

  if (!isEdit.value && !selectedFile) {
    ElMessage.warning('请上传营业执照')
    return
  }
  if (!form.is_long_term && !form.period_end) {
    ElMessage.warning('请填写营业期限截止日期或选择长期')
    return
  }

  submitting.value = true
  try {
    const fd = new FormData()
    fd.append('company_name', form.company_name)
    fd.append('is_long_term', form.is_long_term ? '1' : '0')
    if (!form.is_long_term && form.period_end) {
      fd.append('period_end', form.period_end)
    }
    if (selectedFile) {
      fd.append('license_file', selectedFile)
    }

    let res
    if (isEdit.value) {
      res = await updateCompany(editId.value, fd)
    } else {
      res = await createCompany(fd)
    }

    if (res.success) {
      ElMessage.success(isEdit.value ? '更新成功' : '新增成功')
      if (res.warning) ElMessage.warning(res.warning)
      dialogVisible.value = false
      loadData()
    } else {
      ElMessage.error(res.error)
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.error || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(id) {
  try {
    const res = await deleteCompany(id)
    if (res.success) {
      ElMessage.success('删除成功')
      loadData()
    } else {
      ElMessage.error(res.error)
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.error || '删除失败')
  }
}

function viewFile(folder, filename) {
  if (!filename) return
  window.open(`/api/files/${folder}/${filename}`, '_blank')
}
</script>

<style scoped>
.page-container {
  padding: 20px;
  background: #fff;
  border-radius: 4px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
</style>
