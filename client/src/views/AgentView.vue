<template>
  <div class="page-container">
    <div class="page-header">
      <h3>被代理人管理</h3>
      <el-button type="primary" @click="showAddDialog">新增被代理人</el-button>
    </div>

    <!-- 筛选 -->
    <div class="filter-bar">
      <el-select v-model="filterCompanyId" placeholder="按代理主体筛选" clearable @change="loadData">
        <el-option
          v-for="c in companyOptions"
          :key="c.id"
          :label="c.company_name"
          :value="c.id"
        />
      </el-select>
    </div>

    <el-table :data="agents" v-loading="loading" border stripe>
      <el-table-column prop="company_name" label="代理主体" width="180" />
      <el-table-column prop="agent_name" label="被代理人" min-width="180" />
      <el-table-column label="营业执照" width="100" align="center">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="viewFile('被代理人营业执照', row.license_file)">
            查看
          </el-button>
        </template>
      </el-table-column>
      <el-table-column label="营业期限" width="120">
        <template #default="{ row }">
          {{ row.is_long_term ? '长期' : row.period_end || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="授权委托书" width="100" align="center">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="viewFile('授权委托书', row.auth_file)">
            查看
          </el-button>
        </template>
      </el-table-column>
      <el-table-column prop="auth_expires_on" label="授权截止" width="120" />
      <el-table-column label="操作" width="200" align="center">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="showUpdateAuthDialog(row)">更新授权</el-button>
          <el-button type="info" link size="small" @click="showHistory(row)">历史</el-button>
          <el-popconfirm v-if="userStore.canDelete" title="确定删除？" @confirm="handleDelete(row.id)">
            <template #reference>
              <el-button type="danger" link size="small">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新增弹窗 -->
    <el-dialog v-model="addDialogVisible" title="新增被代理人" width="550px">
      <el-form :model="addForm" ref="addFormRef" label-width="130px">
        <el-form-item label="代理主体" required>
          <el-select v-model="addForm.company_id" placeholder="请选择">
            <el-option v-for="c in companyOptions" :key="c.id" :label="c.company_name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="被代理人名称" required>
          <el-input v-model="addForm.agent_name" placeholder="请输入" />
        </el-form-item>
        <el-form-item label="被代理人营业执照" required>
          <el-upload :auto-upload="false" :limit="1" :on-change="(f) => addForm._licenseFile = f.raw" accept=".jpg,.jpeg,.png,.pdf">
            <el-button size="small" type="primary">选择文件</el-button>
          </el-upload>
        </el-form-item>
        <el-form-item label="营业期限">
          <el-checkbox v-model="addForm.is_long_term">长期</el-checkbox>
          <el-date-picker v-if="!addForm.is_long_term" v-model="addForm.period_end" type="date" value-format="YYYY-MM-DD" placeholder="截止日期" style="margin-left:12px" />
        </el-form-item>
        <el-form-item label="授权委托书" required>
          <el-upload :auto-upload="false" :limit="1" :on-change="(f) => addForm._authFile = f.raw" accept=".jpg,.jpeg,.png,.pdf">
            <el-button size="small" type="primary">选择文件</el-button>
          </el-upload>
        </el-form-item>
        <el-form-item label="授权截止日期" required>
          <el-date-picker v-model="addForm.auth_expires_on" type="date" value-format="YYYY-MM-DD" placeholder="请选择" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleAdd">确定</el-button>
      </template>
    </el-dialog>

    <!-- 更新授权弹窗 -->
    <el-dialog v-model="authDialogVisible" title="更新授权委托书" width="450px">
      <el-form label-width="120px">
        <el-form-item label="授权委托书">
          <el-upload :auto-upload="false" :limit="1" :on-change="(f) => authForm._file = f.raw" accept=".jpg,.jpeg,.png,.pdf">
            <el-button size="small" type="primary">选择文件</el-button>
          </el-upload>
        </el-form-item>
        <el-form-item label="授权截止日期">
          <el-date-picker v-model="authForm.auth_expires_on" type="date" value-format="YYYY-MM-DD" placeholder="请选择" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="authDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleUpdateAuth">确定</el-button>
      </template>
    </el-dialog>

    <!-- 历史弹窗 -->
    <el-dialog v-model="historyDialogVisible" title="授权委托书历史" width="600px">
      <el-table :data="historyData" border size="small">
        <el-table-column prop="auth_expires_on" label="授权截止日期" width="130" />
        <el-table-column label="文件" min-width="200">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="viewFile('授权委托书', row.auth_file)">
              {{ row.auth_file }}
            </el-button>
          </template>
        </el-table-column>
        <el-table-column prop="replaced_at" label="上传时间" width="180" />
        <el-table-column prop="uploaded_by" label="上传人" width="100" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getAgents, createAgent, updateAgentAuth, getAuthHistory, deleteAgent } from '../api/agent'
import { getCompanies } from '../api/company'
import { useUserStore } from '../stores/user'

const userStore = useUserStore()

const agents = ref([])
const companyOptions = ref([])
const loading = ref(false)
const submitting = ref(false)
const filterCompanyId = ref(null)

// 新增
const addDialogVisible = ref(false)
const addFormRef = ref()
const addForm = reactive({
  company_id: null,
  agent_name: '',
  is_long_term: false,
  period_end: '',
  auth_expires_on: '',
  _licenseFile: null,
  _authFile: null,
})

// 更新授权
const authDialogVisible = ref(false)
const authForm = reactive({ agent_id: null, auth_expires_on: '', _file: null })

// 历史
const historyDialogVisible = ref(false)
const historyData = ref([])

onMounted(async () => {
  const res = await getCompanies()
  if (res.success) companyOptions.value = res.data
  loadData()
})

async function loadData() {
  loading.value = true
  try {
    const res = await getAgents(filterCompanyId.value)
    if (res.success) agents.value = res.data
  } finally {
    loading.value = false
  }
}

function showAddDialog() {
  addForm.company_id = null
  addForm.agent_name = ''
  addForm.is_long_term = false
  addForm.period_end = ''
  addForm.auth_expires_on = ''
  addForm._licenseFile = null
  addForm._authFile = null
  addDialogVisible.value = true
}

async function handleAdd() {
  if (!addForm.company_id) return ElMessage.warning('请选择代理主体')
  if (!addForm.agent_name) return ElMessage.warning('请输入被代理人名称')
  if (!addForm._licenseFile) return ElMessage.warning('请上传被代理人营业执照')
  if (!addForm._authFile) return ElMessage.warning('请上传授权委托书')
  if (!addForm.auth_expires_on) return ElMessage.warning('请填写授权截止日期')
  if (!addForm.is_long_term && !addForm.period_end) return ElMessage.warning('请填写营业期限或选择长期')

  submitting.value = true
  try {
    const fd = new FormData()
    fd.append('company_id', addForm.company_id)
    fd.append('agent_name', addForm.agent_name)
    fd.append('is_long_term', addForm.is_long_term ? '1' : '0')
    if (!addForm.is_long_term) fd.append('period_end', addForm.period_end)
    fd.append('auth_expires_on', addForm.auth_expires_on)
    fd.append('license_file', addForm._licenseFile)
    fd.append('auth_file', addForm._authFile)

    const res = await createAgent(fd)
    if (res.success) {
      ElMessage.success('新增成功')
      if (res.warning) ElMessage.warning(res.warning)
      addDialogVisible.value = false
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

function showUpdateAuthDialog(row) {
  authForm.agent_id = row.id
  authForm.auth_expires_on = ''
  authForm._file = null
  authDialogVisible.value = true
}

async function handleUpdateAuth() {
  if (!authForm._file) return ElMessage.warning('请上传授权委托书')
  if (!authForm.auth_expires_on) return ElMessage.warning('请填写授权截止日期')

  submitting.value = true
  try {
    const fd = new FormData()
    fd.append('auth_file', authForm._file)
    fd.append('auth_expires_on', authForm.auth_expires_on)
    const res = await updateAgentAuth(authForm.agent_id, fd)
    if (res.success) {
      ElMessage.success('更新成功')
      if (res.warning) ElMessage.warning(res.warning)
      authDialogVisible.value = false
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

async function showHistory(row) {
  const res = await getAuthHistory(row.id)
  if (res.success) {
    historyData.value = res.data
    historyDialogVisible.value = true
  }
}

async function handleDelete(id) {
  try {
    const res = await deleteAgent(id)
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
.page-container { padding: 20px; background: #fff; border-radius: 4px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.filter-bar { margin-bottom: 16px; }
</style>
