<template>
  <div class="page-container">
    <div class="page-header">
      <h3>作品管理</h3>
      <div>
        <el-button type="success" :disabled="selectedWorks.length === 0" @click="handlePackage">
          打包下载{{ selectedWorks.length > 0 ? `(${selectedWorks.length})` : '' }}
        </el-button>
        <el-button type="primary" @click="showAddDialog" style="margin-left: 12px">添加作品</el-button>
      </div>
    </div>

    <!-- 筛选 -->
    <div class="filter-bar">
      <el-input
        v-model="searchKeywords"
        placeholder="搜索作品名称或别名（多个用_分隔，如：作品1_别名2）"
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

    <!-- 搜索关键词未匹配提示 -->
    <div v-if="unmatchedKeywords.length > 0" class="search-warning">
      搜索内容中，{{ unmatchedKeywords.join('、') }} 没有匹配出数据
    </div>

    <el-table :data="works" v-loading="loading" border stripe @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="55" />
      <el-table-column prop="company_name" label="代理主体" width="160" />
      <el-table-column prop="agent_name" label="被代理人" width="160" />
      <el-table-column prop="work_name" label="作品名称" min-width="180" />
      <el-table-column prop="alias" label="别名" min-width="150" />
      <el-table-column label="权属证明" width="100" align="center">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click="viewFile('权属证明', row.proof_file)">
            查看
          </el-button>
        </template>
      </el-table-column>
      <el-table-column label="其他证明" width="100" align="center">
        <template #default="{ row }">
          <el-button
            v-if="(row.other_files || []).length > 0"
            type="primary"
            link
            size="small"
            @click="showOtherFiles(row)"
          >
            查看({{ row.other_files.length }})
          </el-button>
          <span v-else>-</span>
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
        <el-form-item label="别名">
          <el-input v-model="addForm.alias" placeholder="多个别名请用下划线_拼接（可选）" />
        </el-form-item>
        <el-form-item label="权属证明" required>
          <el-upload ref="proofUploadRef" :auto-upload="false" :limit="1" :on-change="(f) => addForm._proofFile = f.raw" accept=".jpg,.jpeg,.png,.pdf">
            <el-button size="small" type="primary">选择文件</el-button>
          </el-upload>
        </el-form-item>
        <el-form-item label="其他证明">
          <el-upload ref="otherUploadRef" :auto-upload="false" :limit="2" :on-change="handleOtherChange" multiple accept=".jpg,.jpeg,.png,.pdf">
            <el-button size="small">选择文件（最多2个）</el-button>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleAdd">确定</el-button>
      </template>
    </el-dialog>

    <!-- 查看其他证明弹窗 -->
    <el-dialog v-model="otherFilesDialogVisible" title="其他证明文件" width="450px">
      <div class="other-files-list">
        <div
          v-for="(file, index) in currentOtherFiles"
          :key="index"
          class="file-item"
          @click="viewFile('权属证明', file)"
        >
          <el-icon><Document /></el-icon>
          <span class="file-name">{{ file }}</span>
        </div>
      </div>
      <template #footer>
        <el-button @click="otherFilesDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 打包体积限制弹窗 -->
    <el-dialog v-model="packageDialogVisible" title="打包下载" width="400px">
      <el-form label-width="160px">
        <el-form-item label="单文件打包最大体积(MB)">
          <el-input-number v-model="maxPackageSize" :min="1" :max="1000" :precision="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="packageDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="packaging" @click="confirmPackage">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Document } from '@element-plus/icons-vue'
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
const unmatchedKeywords = ref([])
const selectedWorks = ref([])

let searchTimer = null
function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => loadData(), 400)
}
onUnmounted(() => clearTimeout(searchTimer))

const addDialogVisible = ref(false)
const proofUploadRef = ref(null)
const otherUploadRef = ref(null)
const otherFilesDialogVisible = ref(false)
const currentOtherFiles = ref([])
const packageDialogVisible = ref(false)
const maxPackageSize = ref(18)
const packaging = ref(false)
const addForm = reactive({
  company_id: null,
  agent_id: null,
  work_name: '',
  alias: '',
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
    if (res.success) {
      let resultWorks = res.data

      // 检查未匹配的关键词，并按关键词热度排序
      unmatchedKeywords.value = []
      if (searchKeywords.value) {
        const keywords = searchKeywords.value.split('_').map(k => k.trim()).filter(k => k)
        const matchedSet = new Set()

        // 统计每个关键词匹配了多少部作品
        const keywordMatchCount = {}
        keywords.forEach(kw => {
          keywordMatchCount[kw] = 0
        })

        resultWorks.forEach(w => {
          keywords.forEach(kw => {
            let matched = false
            // 检查作品名称
            if (w.work_name.includes(kw)) {
              matched = true
            }
            // 检查别名（别名也按下划线拆分）
            if (!matched && w.alias) {
              const aliases = w.alias.split('_').map(a => a.trim()).filter(a => a)
              if (aliases.some(alias => alias.includes(kw))) {
                matched = true
              }
            }
            if (matched) {
              matchedSet.add(kw)
              keywordMatchCount[kw]++
            }
          })
        })

        // 给每部作品计算权重（匹配到的关键词中，取最高的匹配数量）
        resultWorks = resultWorks.map(w => {
          let maxWeight = 0
          keywords.forEach(kw => {
            let matched = false
            if (w.work_name.includes(kw)) {
              matched = true
            }
            if (!matched && w.alias) {
              const aliases = w.alias.split('_').map(a => a.trim()).filter(a => a)
              if (aliases.some(alias => alias.includes(kw))) {
                matched = true
              }
            }
            if (matched && keywordMatchCount[kw] > maxWeight) {
              maxWeight = keywordMatchCount[kw]
            }
          })
          return { ...w, _weight: maxWeight }
        })

        // 按权重从高到低排序
        resultWorks.sort((a, b) => b._weight - a._weight)

        unmatchedKeywords.value = keywords.filter(kw => !matchedSet.has(kw))
      }

      works.value = resultWorks
    }
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
  addForm.alias = ''
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
    if (addForm.alias.trim()) {
      fd.append('alias', addForm.alias.trim())
    }
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
      addForm.alias = ''
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

function showOtherFiles(row) {
  currentOtherFiles.value = row.other_files || []
  otherFilesDialogVisible.value = true
}

function handleSelectionChange(selection) {
  selectedWorks.value = selection
}

async function handlePackage() {
  if (selectedWorks.value.length === 0) {
    return ElMessage.warning('请选择要打包的作品')
  }
  packageDialogVisible.value = true
}

async function confirmPackage() {
  const workIds = selectedWorks.value.map(w => w.id)
  packaging.value = true
  try {
    const response = await fetch('/api/works/package', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        work_ids: workIds,
        max_size_mb: maxPackageSize.value
      })
    })

    if (!response.ok) {
      const error = await response.json()
      return ElMessage.error(error.error || '打包失败')
    }

    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const filename = response.headers.get('Content-Disposition')?.match(/filename="(.+)"/)?.[1] || 'works.zip'
    a.download = decodeURIComponent(filename)
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
    ElMessage.success('打包成功')
    packageDialogVisible.value = false
  } catch (e) {
    ElMessage.error('打包失败：' + e.message)
  } finally {
    packaging.value = false
  }
}
</script>

<style scoped>
.page-container { padding: 20px; background: #fff; border-radius: 4px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.filter-bar { margin-bottom: 16px; display: flex; align-items: center; }
.search-warning { margin-bottom: 12px; color: #f56c6c; font-size: 14px; }
.other-files-list { max-height: 400px; overflow-y: auto; }
.file-item {
  display: flex;
  align-items: center;
  padding: 12px;
  margin-bottom: 8px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}
.file-item:hover {
  background: #f5f7fa;
  border-color: #409eff;
}
.file-item .el-icon {
  margin-right: 8px;
  font-size: 18px;
  color: #409eff;
}
.file-name {
  flex: 1;
  color: #606266;
  word-break: break-all;
}
</style>
