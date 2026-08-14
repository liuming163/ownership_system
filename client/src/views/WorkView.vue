<template>
  <div class="page-container">
    <div class="page-header">
      <h3>作品管理</h3>
      <el-button type="primary" @click="showAddDialog">添加作品</el-button>
    </div>

    <!-- 筛选 -->
    <div class="filter-bar">
      <el-input
        v-model="searchKeywords"
        placeholder="搜索作品名称（多个用_分隔，如：作品1_作品2）"
        clearable
        @input="onSearchInput"
        style="margin-right: 12px; flex: 1"
      />
      <el-select v-model="filterCompanyId" placeholder="代理主体" clearable @change="onCompanyChange" style="width: 320px; margin-right: 12px">
        <el-option v-for="c in companyOptions" :key="c.id" :label="c.company_name" :value="c.id" />
      </el-select>
      <el-select v-model="filterAgentId" placeholder="被代理人" clearable @change="loadData" style="width: 320px">
        <el-option v-for="a in agentOptions" :key="a.id" :label="a.agent_name" :value="a.id" />
      </el-select>
    </div>

    <el-table :data="works" v-loading="loading" border stripe>
      <el-table-column prop="company_name" label="代理主体" width="160" />
      <el-table-column prop="agent_name" label="被代理人" width="160" />
      <el-table-column prop="work_name" label="作品名称" min-width="180" />
      <el-table-column label="权属证明" width="100" align="center">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="viewFile('权属证明', row.proof_file)">
            查看
          </el-button>
        </template>
      </el-table-column>
      <el-table-column label="其他证明" width="100" align="center">
        <template #default="{ row }">
          <span>{{ (row.other_files || []).length }}个</span>
        </template>
      </el-table-column>
      <el-table-column prop="created_by" label="创建人" width="100" />
      <el-table-column prop="created_at" label="创建时间" width="180" />
      <el-table-column label="操作" width="120" align="center">
        <template #default="{ row }">
          <el-popconfirm title="确定删除该作品？" @confirm="handleDelete(row.id)">
            <template #reference>
              <el-button type="danger" link size="small">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新增作品弹窗 -->
    <el-dialog v-model="addDialogVisible" title="添加作品" width="550px">
      <el-form :model="addForm" label-width="110px">
        <el-form-item label="代理主体" required>
          <el-select v-model="addForm.company_id" placeholder="请选择" @change="onAddCompanyChange">
            <el-option v-for="c in companyOptions" :key="c.id" :label="c.company_name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="被代理人" required>
          <el-select v-model="addForm.agent_id" placeholder="请先选择代理主体">
            <el-option v-for="a in addAgentOptions" :key="a.id" :label="a.agent_name" :value="a.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="作品名称" required>
          <el-input v-model="addForm.work_name" placeholder="请输入作品名称" />
        </el-form-item>
        <el-form-item label="权属证明" required>
          <el-upload ref="proofUploadRef" :auto-upload="false" :limit="1" :on-change="(f) => addForm._proofFile = f.raw" accept=".jpg,.jpeg,.png,.pdf">
            <el-button size="small" type="primary">选择文件</el-button>
          </el-upload>
        </el-form-item>
        <el-form-item label="其他证明">
          <el-upload ref="otherUploadRef" :auto-upload="false" :limit="5" :on-change="handleOtherChange" multiple accept=".jpg,.jpeg,.png,.pdf">
            <el-button size="small">选择文件（可多个）</el-button>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleAdd">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getWorks, createWork, deleteWork } from '../api/work'
import { getCompanies } from '../api/company'
import { getAgents } from '../api/agent'

const works = ref([])
const companyOptions = ref([])
const agentOptions = ref([])
const addAgentOptions = ref([])
const loading = ref(false)
const submitting = ref(false)
const filterCompanyId = ref(null)
const filterAgentId = ref(null)
const searchKeywords = ref('')

let searchTimer = null
function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => loadData(), 400)
}
onUnmounted(() => clearTimeout(searchTimer))

const addDialogVisible = ref(false)
const proofUploadRef = ref(null)
const otherUploadRef = ref(null)
const addForm = reactive({
  company_id: null,
  agent_id: null,
  work_name: '',
  _proofFile: null,
  _otherFiles: [],
})

onMounted(async () => {
  const res = await getCompanies()
  if (res.success) companyOptions.value = res.data
  loadData()
})

async function loadData() {
  loading.value = true
  try {
    const params = {}
    if (filterCompanyId.value) params.company_id = filterCompanyId.value
    if (filterAgentId.value) params.agent_id = filterAgentId.value
    if (searchKeywords.value) params.search = searchKeywords.value
    const res = await getWorks(params)
    if (res.success) works.value = res.data
  } finally {
    loading.value = false
  }
}

async function onCompanyChange(val) {
  filterAgentId.value = null
  if (val) {
    const res = await getAgents(val)
    if (res.success) agentOptions.value = res.data
  } else {
    agentOptions.value = []
  }
  loadData()
}

async function onAddCompanyChange(val) {
  addForm.agent_id = null
  if (val) {
    const res = await getAgents(val)
    if (res.success) addAgentOptions.value = res.data
  } else {
    addAgentOptions.value = []
  }
}

function showAddDialog() {
  addForm.company_id = null
  addForm.agent_id = null
  addForm.work_name = ''
  addForm._proofFile = null
  addForm._otherFiles = []
  addAgentOptions.value = []
  addDialogVisible.value = true
}

function handleOtherChange(file, fileList) {
  addForm._otherFiles = fileList.map(f => f.raw)
}

async function handleAdd() {
  if (!addForm.company_id) return ElMessage.warning('请选择代理主体')
  if (!addForm.agent_id) return ElMessage.warning('请选择被代理人')
  if (!addForm.work_name.trim()) return ElMessage.warning('请输入作品名称')
  if (!addForm._proofFile) return ElMessage.warning('请上传权属证明文件')

  submitting.value = true
  try {
    const fd = new FormData()
    fd.append('company_id', addForm.company_id)
    fd.append('agent_id', addForm.agent_id)
    fd.append('work_name', addForm.work_name.trim())
    fd.append('proof_file', addForm._proofFile)
    for (const f of addForm._otherFiles) {
      fd.append('other_files', f)
    }

    const res = await createWork(fd)
    if (res.success) {
      ElMessage.success('添加成功')
      addDialogVisible.value = false
      // 清空表单和上传文件
      addForm.company_id = null
      addForm.agent_id = null
      addForm.work_name = ''
      addForm._proofFile = null
      addForm._otherFiles = []
      addAgentOptions.value = []
      proofUploadRef.value?.clearFiles()
      otherUploadRef.value?.clearFiles()
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
    const res = await deleteWork(id)
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
.filter-bar { margin-bottom: 16px; display: flex; align-items: center; }
</style>
