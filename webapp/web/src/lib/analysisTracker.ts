/**
 * 分析任务追踪器 - 使用 localStorage 跟踪进行中的分析任务
 */

export interface AnalysisTask {
  taskId: string
  tsCode: string
  stockName?: string
  progress: number
  message: string
  startedAt: string
}

const STORAGE_KEY = 'active_analyses'
const COMPLETED_KEY = 'completed_analyses'

/**
 * 获取所有进行中的分析任务
 */
export function getActiveAnalyses(): AnalysisTask[] {
  try {
    const data = localStorage.getItem(STORAGE_KEY)
    if (!data) return []
    const tasks = JSON.parse(data) as AnalysisTask[]
    // 过滤掉超过 10 分钟的任务（可能是异常中断的）
    const tenMinutesAgo = Date.now() - 10 * 60 * 1000
    return tasks.filter(t => new Date(t.startedAt).getTime() > tenMinutesAgo)
  } catch {
    return []
  }
}

/**
 * 添加或更新分析任务
 */
export function upsertAnalysis(task: AnalysisTask): void {
  const tasks = getActiveAnalyses()
  const idx = tasks.findIndex(t => t.tsCode === task.tsCode)
  if (idx >= 0) {
    tasks[idx] = task
  } else {
    tasks.unshift(task)
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks))
  // 触发 storage 事件让其他标签页也能感知
  window.dispatchEvent(new StorageEvent('storage', { key: STORAGE_KEY }))
}

/**
 * 更新任务进度
 */
export function updateProgress(tsCode: string, progress: number, message: string): void {
  const tasks = getActiveAnalyses()
  const task = tasks.find(t => t.tsCode === tsCode)
  if (task) {
    task.progress = progress
    task.message = message
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks))
    window.dispatchEvent(new StorageEvent('storage', { key: STORAGE_KEY }))
  }
}

/**
 * 移除已完成的分析任务
 */
export function removeAnalysis(tsCode: string): void {
  const tasks = getActiveAnalyses().filter(t => t.tsCode !== tsCode)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks))
  window.dispatchEvent(new StorageEvent('storage', { key: STORAGE_KEY }))
}

/**
 * 检查某个股票是否正在分析中
 */
export function isAnalyzing(tsCode: string): boolean {
  return getActiveAnalyses().some(t => t.tsCode === tsCode)
}

/**
 * 已完成但未读的分析任务
 */
export interface CompletedAnalysis {
  tsCode: string
  stockName: string
  reportId: string
  score: number
  completedAt: string
  read: boolean
}

/**
 * 获取已完成的分析任务
 */
export function getCompletedAnalyses(): CompletedAnalysis[] {
  try {
    const data = localStorage.getItem(COMPLETED_KEY)
    if (!data) return []
    const items = JSON.parse(data) as CompletedAnalysis[]
    // 只保留最近 24 小时的
    const oneDayAgo = Date.now() - 24 * 60 * 60 * 1000
    return items.filter(t => new Date(t.completedAt).getTime() > oneDayAgo)
  } catch {
    return []
  }
}

/**
 * 添加已完成的分析
 */
export function addCompletedAnalysis(item: Omit<CompletedAnalysis, 'read' | 'completedAt'>): void {
  const items = getCompletedAnalyses()
  // 移除同一股票的旧记录
  const filtered = items.filter(t => t.tsCode !== item.tsCode)
  filtered.unshift({
    ...item,
    completedAt: new Date().toISOString(),
    read: false,
  })
  localStorage.setItem(COMPLETED_KEY, JSON.stringify(filtered))
  // 触发事件通知其他页面
  window.dispatchEvent(new StorageEvent('storage', { key: COMPLETED_KEY }))
}

/**
 * 获取未读数量
 */
export function getUnreadCount(): number {
  return getCompletedAnalyses().filter(t => !t.read).length
}

/**
 * 标记某个报告为已读
 */
export function markAsRead(reportId: string): void {
  const items = getCompletedAnalyses()
  const item = items.find(t => t.reportId === reportId)
  if (item) {
    item.read = true
    localStorage.setItem(COMPLETED_KEY, JSON.stringify(items))
    window.dispatchEvent(new StorageEvent('storage', { key: COMPLETED_KEY }))
  }
}

/**
 * 标记所有为已读
 */
export function markAllAsRead(): void {
  const items = getCompletedAnalyses()
  items.forEach(t => t.read = true)
  localStorage.setItem(COMPLETED_KEY, JSON.stringify(items))
  window.dispatchEvent(new StorageEvent('storage', { key: COMPLETED_KEY }))
}
