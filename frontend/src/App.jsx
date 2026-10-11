import React, { useCallback, useEffect, useMemo, useState } from 'react'

const PAGE_SIZE = 10

function Icon({ name, size = 20 }) {
  const paths = {
    activity: <><path d="M3 12h4l3-7 4 14 3-7h4" /></>,
    arrow: <><path d="M5 12h14m-6-6 6 6-6 6" /></>,
    back: <><path d="M19 12H5m6 6-6-6 6-6" /></>,
    check: <><path d="m5 12 4 4L19 6" /></>,
    chevron: <><path d="m9 18 6-6-6-6" /></>,
    close: <><path d="M18 6 6 18M6 6l12 12" /></>,
    download: <><path d="M12 3v12m-4-4 4 4 4-4M4 17v3h16v-3" /></>,
    file: <><path d="M7 3h7l4 4v14H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z" /><path d="M14 3v5h5M8 13h8M8 17h6" /></>,
    filter: <><path d="M4 6h16M7 12h10m-7 6h4" /></>,
    layers: <><path d="m12 3 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5M3 16l9 5 9-5" /></>,
    search: <><circle cx="11" cy="11" r="7" /><path d="m16 16 5 5" /></>,
    shield: <><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" /><path d="m9 12 2 2 4-4" /></>,
    trash: <><path d="M4 7h16M10 4h4m-8 3 1 14h10l1-14M10 11v6m4-6v6" /></>,
    upload: <><path d="M12 16V3m-5 5 5-5 5 5M4 17v4h16v-4" /></>,
  }
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>
}

async function request(path, options = {}) {
  const response = await fetch(path, options)
  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json') ? await response.json() : null
  if (!response.ok) throw new Error(payload?.detail || `请求失败（${response.status}）`)
  return payload
}

function formatTime(value) {
  return value ? value.replace('T', ' ').slice(0, 19) : '—'
}

function formatSize(bytes) {
  if (!bytes) return '0 KB'
  return `${(bytes / 1024).toFixed(1)} KB`
}

function orderFromPath() {
  const match = window.location.pathname.match(/^\/orders\/([^/]+)$/)
  return match ? decodeURIComponent(match[1]) : null
}

function extractOrderId(filename) {
  const stem = filename.replace(/\.[^.]+$/, '')
  if (stem.startsWith('BMS_')) return stem.split('_')[2]?.split('.')[0] || filename
  return filename
}

function UploadDialog({ orders, onClose, onUploaded, onOpenOrder }) {
  const [files, setFiles] = useState([])
  const [dragging, setDragging] = useState(false)
  const [replace, setReplace] = useState(false)
  const [busy, setBusy] = useState(false)
  const [results, setResults] = useState(null)
  const [error, setError] = useState('')
  const existingIds = new Set(orders.map(item => item.order_id))
  const ids = files.map(file => extractOrderId(file.name))
  const duplicates = ids.filter((id, index) => ids.indexOf(id) !== index)
  const replacements = [...new Set(ids.filter(id => existingIds.has(id)))]

  useEffect(() => {
    const handleEscape = event => { if (event.key === 'Escape' && !busy) onClose() }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [busy, onClose])

  async function submit() {
    if (!files.length || duplicates.length || (replacements.length && !replace)) return
    const body = new FormData()
    files.forEach(file => body.append('files', file))
    body.append('replace', String(replace))
    setBusy(true)
    setError('')
    try {
      const data = await request('/api/orders/upload', { method: 'POST', body })
      setResults(data.results)
      if (data.results.some(item => item.ok)) await onUploaded()
    } catch (cause) {
      setError(cause.message)
    } finally {
      setBusy(false)
    }
  }

  function addFiles(selected) {
    const next = [...selected].filter(file => file.name.toLowerCase().endsWith('.txt'))
    setFiles(previous => [...previous, ...next])
    setReplace(false)
    setResults(null)
  }

  return <div className="modal-backdrop" onMouseDown={event => { if (event.target === event.currentTarget && !busy) onClose() }}>
    <section className="modal" role="dialog" aria-modal="true" aria-labelledby="upload-title">
      <div className="modal-head">
        <div><div className="eyebrow">新建解析</div><h2 id="upload-title">上传并解析报文</h2><p>选择 TXT 文件，系统自动提取订单号并保存解析结果。</p></div>
        <button className="icon-button" onClick={onClose} disabled={busy} aria-label="关闭"><Icon name="close" /></button>
      </div>
      {!results && <>
        <label className={`dropzone ${dragging ? 'dragging' : ''}`}
          onDragOver={event => { event.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={event => { event.preventDefault(); setDragging(false); addFiles(event.dataTransfer.files) }}>
          <input type="file" accept=".txt,text/plain" multiple onChange={event => { addFiles(event.target.files); event.target.value = '' }} />
          <span className="drop-icon"><Icon name="upload" size={28} /></span>
          <strong>拖拽文件到这里，或点击选择</strong>
          <span>支持多选 .txt 文件，单文件最大 50 MB</span>
        </label>
        {!!files.length && <div className="upload-files">
          <div className="upload-files-title">待解析文件 <span>{files.length} 个</span></div>
          {files.map((file, index) => <div className="upload-file" key={`${file.name}-${index}`}>
            <span className="file-icon"><Icon name="file" size={18} /></span>
            <span className="upload-file-name"><strong title={file.name}>{file.name}</strong><small>订单 {extractOrderId(file.name)} · {formatSize(file.size)}</small></span>
            <button className="icon-button" aria-label={`移除 ${file.name}`} onClick={() => { setFiles(files.filter((_, itemIndex) => itemIndex !== index)); setReplace(false) }}><Icon name="close" size={17} /></button>
          </div>)}
        </div>}
        {!!duplicates.length && <div className="notice error">所选文件存在相同订单号：{[...new Set(duplicates)].join('、')}。请每个订单只保留一个文件。</div>}
        {!!replacements.length && <div className="notice warning"><strong>检测到已有订单：</strong>{replacements.join('、')}<label className="confirm-line"><input type="checkbox" checked={replace} onChange={event => setReplace(event.target.checked)} /> 我确认用新文件替换这些订单的原文件和解析结果</label></div>}
        {error && <div className="notice error">{error}</div>}
      </>}
      {results && <div className="upload-results">
        <div className={`result-summary ${results.every(item => !item.ok) ? 'failed' : ''}`}><span className="result-check"><Icon name={results.every(item => !item.ok) ? 'close' : 'check'} size={22} /></span><div><strong>{results.every(item => !item.ok) ? '解析失败' : '处理完成'}</strong><p>成功 {results.filter(item => item.ok).length} 个，失败 {results.filter(item => !item.ok).length} 个</p></div></div>
        {results.map((item, index) => <div className="result-item" key={`${item.filename}-${index}`}><div><strong>{item.filename}</strong><small>{item.ok ? `订单 ${item.order_id} · ${item.message_count.toLocaleString()} 条报文` : item.error}</small></div><span className={`badge ${item.ok ? 'success' : 'danger'}`}>{item.ok ? '已完成' : '失败'}</span></div>)}
      </div>}
      <div className="modal-actions">
        <button className="button secondary" onClick={onClose} disabled={busy}>{results ? '完成' : '取消'}</button>
        {!results && <button className="button primary" onClick={submit} disabled={busy || !files.length || !!duplicates.length || (!!replacements.length && !replace)}>{busy ? '正在解析…' : files.length ? `开始解析 ${files.length} 个文件` : '开始解析'}</button>}
        {results?.filter(item => item.ok).length === 1 && <button className="button primary" onClick={() => onOpenOrder(results.find(item => item.ok).order_id)}>查看解析结果 <Icon name="arrow" size={17} /></button>}
      </div>
    </section>
  </div>
}

function DeleteDialog({ count, onClose, onConfirm, busy }) {
  return <div className="modal-backdrop" onMouseDown={event => { if (event.target === event.currentTarget && !busy) onClose() }}>
    <section className="modal narrow" role="dialog" aria-modal="true" aria-labelledby="delete-title">
      <div className="modal-head"><div><div className="eyebrow danger-text">删除确认</div><h2 id="delete-title">删除 {count} 个订单？</h2><p>原始文件和解析结果都会删除，此操作无法在系统内撤销。</p></div><button className="icon-button" onClick={onClose} disabled={busy} aria-label="关闭"><Icon name="close" /></button></div>
      <div className="modal-actions"><button className="button secondary" onClick={onClose} disabled={busy}>取消</button><button className="button danger-button" onClick={onConfirm} disabled={busy}>{busy ? '正在删除…' : '确认删除'}</button></div>
    </section>
  </div>
}

function Dashboard({ orders, loading, error, onUpload, onView, onDelete }) {
  const [query, setQuery] = useState('')
  const [advanced, setAdvanced] = useState(false)
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [sort, setSort] = useState('newest')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState([])

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase()
    const items = orders.filter(item =>
      (!term || item.order_id.toLowerCase().includes(term) || item.filename.toLowerCase().includes(term)) &&
      (!start || item.upload_time.slice(0, 10) >= start) && (!end || item.upload_time.slice(0, 10) <= end),
    )
    items.sort((a, b) => sort === 'oldest' ? a.upload_time.localeCompare(b.upload_time) : sort === 'id' ? a.order_id.localeCompare(b.order_id) : b.upload_time.localeCompare(a.upload_time))
    return items
  }, [orders, query, start, end, sort])
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const currentPage = Math.min(page, pageCount)
  const visible = filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)
  const selectedVisible = visible.filter(item => selected.includes(item.order_id))
  const totalMessages = orders.reduce((sum, item) => sum + item.message_count, 0)
  const latest = orders[0]?.upload_time

  function resetFilters() { setQuery(''); setStart(''); setEnd(''); setSort('newest'); setPage(1) }
  function toggleSelected(id) { setSelected(previous => previous.includes(id) ? previous.filter(item => item !== id) : [...previous, id]) }

  return <>
    <div className="page-intro"><div className="eyebrow">工作台 / 概览</div><h1>充电报文解析</h1><p>上传原始报文，快速定位订单，查看每一条解析结果。</p></div>
    <div className="stats-grid">
      <div className="metric-card"><span className="metric-icon teal"><Icon name="layers" /></span><div><small>订单总数</small><strong>{orders.length.toLocaleString()}</strong><span>已保存的解析记录</span></div></div>
      <div className="metric-card"><span className="metric-icon blue"><Icon name="activity" /></span><div><small>已解析报文</small><strong>{totalMessages.toLocaleString()}</strong><span>全部订单合计</span></div></div>
      <div className="metric-card"><span className="metric-icon amber"><Icon name="file" /></span><div><small>最近上传</small><strong className="date-value">{latest ? formatTime(latest).slice(0, 16) : '—'}</strong><span>本地时间</span></div></div>
    </div>

    <section className="records-section">
      <div className="section-title"><div><div className="eyebrow">订单记录</div><h2>解析记录 <span>{filtered.length}</span></h2><p>从订单号或文件名查找，并进入报文明细。</p></div><button className="button primary desktop-upload" onClick={onUpload}><Icon name="upload" size={18} /> 上传并解析</button></div>
      <div className="toolbar"><div className="search-field"><Icon name="search" size={18} /><input aria-label="搜索订单号或文件名" placeholder="搜索订单号或文件名" value={query} onChange={event => { setQuery(event.target.value); setPage(1) }} /></div><button className={`button filter-button ${advanced ? 'active' : 'secondary'}`} onClick={() => setAdvanced(!advanced)}><Icon name="filter" size={18} /> 筛选与排序</button></div>
      {advanced && <div className="advanced-filters"><label>上传起始日期<input type="date" value={start} onChange={event => { setStart(event.target.value); setPage(1) }} /></label><label>上传截止日期<input type="date" value={end} onChange={event => { setEnd(event.target.value); setPage(1) }} /></label><label>排序方式<select value={sort} onChange={event => setSort(event.target.value)}><option value="newest">上传时间：新到旧</option><option value="oldest">上传时间：旧到新</option><option value="id">订单号：升序</option></select></label><button className="text-button" onClick={resetFilters}>重置条件</button></div>}
      {!!selected.length && <div className="selection-bar"><span>已选择 {selected.length} 个订单</span><button className="button danger-outline" onClick={() => onDelete(selected, () => setSelected([]))}><Icon name="trash" size={16} /> 删除所选</button></div>}
      {error && <div className="notice error">{error}</div>}
      <div className="table-panel">
        <div className="orders-table-wrap"><table className="orders-table"><thead><tr><th><input type="checkbox" aria-label="选择当前页" checked={!!visible.length && selectedVisible.length === visible.length} onChange={event => setSelected(previous => event.target.checked ? [...new Set([...previous, ...visible.map(item => item.order_id)])] : previous.filter(id => !visible.some(item => item.order_id === id)))} /></th><th>订单号</th><th>源文件</th><th>状态</th><th className="numeric">报文数</th><th>上传时间</th><th></th></tr></thead><tbody>
          {visible.map(item => <tr key={item.order_id}><td><input type="checkbox" aria-label={`选择订单 ${item.order_id}`} checked={selected.includes(item.order_id)} onChange={() => toggleSelected(item.order_id)} /></td><td><button className="order-link" onClick={() => onView(item.order_id)}>{item.order_id}</button></td><td><div className="filename" title={item.filename}>{item.filename}</div><small>{formatSize(item.file_size)}</small></td><td><span className="badge success"><span className="badge-dot" />{item.status || '已完成'}</span></td><td className="numeric strong">{item.message_count.toLocaleString()}</td><td className="muted nowrap">{formatTime(item.upload_time)}</td><td><button className="row-action" onClick={() => onView(item.order_id)} aria-label={`查看订单 ${item.order_id}`}><Icon name="chevron" size={18} /></button></td></tr>)}
        </tbody></table></div>
        {!loading && !filtered.length && <div className="empty-state"><span className="empty-icon"><Icon name={orders.length ? 'search' : 'file'} size={28} /></span><h3>{orders.length ? '没有找到符合条件的订单' : '还没有解析记录'}</h3><p>{orders.length ? '试试更换关键词或重置筛选条件。' : '上传 TXT 报文文件，即可开始第一次解析。'}</p>{!orders.length && <button className="button primary" onClick={onUpload}>上传报文</button>}</div>}
        {loading && <div className="empty-state"><p>正在读取订单…</p></div>}
        {!!filtered.length && <div className="table-footer"><span>显示 {(currentPage - 1) * PAGE_SIZE + 1}–{Math.min(currentPage * PAGE_SIZE, filtered.length)} 条，共 {filtered.length} 条</span><div className="pagination"><button disabled={currentPage <= 1} onClick={() => setPage(currentPage - 1)}>上一页</button><span>{currentPage} / {pageCount}</span><button disabled={currentPage >= pageCount} onClick={() => setPage(currentPage + 1)}>下一页</button></div></div>}
      </div>
    </section>
  </>
}

function OrderDetail({ orderId, onBack }) {
  const [detail, setDetail] = useState(null)
  const [rows, setRows] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [phase, setPhase] = useState('')
  const [name, setName] = useState('')
  const [query, setQuery] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    setLoading(true)
    request(`/api/orders/${encodeURIComponent(orderId)}`).then(data => { if (active) { setDetail(data); setError('') } }).catch(cause => { if (active) setError(cause.message) }).finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [orderId])

  useEffect(() => {
    let active = true
    const params = new URLSearchParams({ page: String(page), page_size: '50' })
    if (phase) params.set('phase', phase)
    if (name) params.set('name', name)
    if (query) params.set('q', query)
    request(`/api/orders/${encodeURIComponent(orderId)}/messages?${params}`).then(data => { if (active) { setRows(data.rows); setTotal(data.total) } }).catch(cause => { if (active) setError(cause.message) })
    return () => { active = false }
  }, [orderId, page, phase, name, query])

  if (loading) return <div className="empty-state"><p>正在加载解析结果…</p></div>
  if (error && !detail) return <div className="empty-state"><h3>无法打开订单</h3><p>{error}</p><button className="button secondary" onClick={onBack}>返回解析记录</button></div>
  if (!detail) return null

  const { order, phases, types, unknown_count: unknownCount } = detail
  const pageCount = Math.max(1, Math.ceil(total / 50))
  const maxPhase = Math.max(1, ...Object.values(phases))
  const exportUrl = format => `/api/orders/${encodeURIComponent(orderId)}/export/${format}`

  return <>
    <button className="back-link" onClick={onBack}><Icon name="back" size={17} /> 返回解析记录</button>
    <div className="detail-heading"><div><div className="eyebrow">订单详情 / 解析结果</div><h1>订单 {orderId}</h1><p title={order.filename}>{order.filename}</p></div><span className="badge success large"><span className="badge-dot" />{order.status}</span></div>
    <div className="detail-metrics"><div><small>有效报文</small><strong>{order.message_count.toLocaleString()}</strong></div><div><small>阶段数量</small><strong>{Object.keys(phases).length}</strong></div><div><small>报文类型</small><strong>{Object.keys(types).length}</strong></div><div><small>未识别帧</small><strong>{unknownCount.toLocaleString()}</strong></div><div><small>源文件大小</small><strong className="smaller">{formatSize(order.file_size)}</strong></div></div>
    <div className="detail-grid"><section className="card phase-card"><div className="card-heading"><h2>阶段分布</h2><span>按有效报文统计</span></div>{Object.entries(phases).sort((a, b) => b[1] - a[1]).map(([label, count]) => <div className="phase-row" key={label}><span>{label}</span><div className="phase-track"><div style={{ width: `${Math.max(3, count / maxPhase * 100)}%` }} /></div><strong>{count.toLocaleString()}</strong></div>)}</section><section className="card export-card"><div className="card-heading"><h2>导出结果</h2><span>保留原始数据和解析记录</span></div><div className="export-list"><a href={exportUrl('excel')}><span className="export-symbol xls">X</span><span><strong>Excel 表格</strong><small>适合筛选与统计</small></span><Icon name="download" size={18} /></a><a href={exportUrl('json')}><span className="export-symbol json">{`{}`}</span><span><strong>JSON 数据</strong><small>适合程序继续处理</small></span><Icon name="download" size={18} /></a><a href={exportUrl('txt')}><span className="export-symbol txt">T</span><span><strong>TXT 解析报告</strong><small>便于阅读和留档</small></span><Icon name="download" size={18} /></a><a href={exportUrl('original')}><span className="export-symbol raw"><Icon name="file" size={18} /></span><span><strong>下载原文件</strong><small>未修改的上传内容</small></span><Icon name="download" size={18} /></a></div></section></div>
    <section className="messages-section"><div className="section-title"><div><div className="eyebrow">报文记录</div><h2>报文明细 <span>{total.toLocaleString()}</span></h2><p>按阶段和报文类型定位，查看完整解析内容。</p></div></div><div className="message-toolbar"><div className="search-field"><Icon name="search" size={18} /><input aria-label="搜索解析内容" placeholder="搜索报文名、时间或解析内容" value={query} onChange={event => { setQuery(event.target.value); setPage(1) }} /></div><select aria-label="筛选阶段" value={phase} onChange={event => { setPhase(event.target.value); setPage(1) }}><option value="">全部阶段</option>{Object.keys(phases).map(item => <option key={item}>{item}</option>)}</select><select aria-label="筛选报文" value={name} onChange={event => { setName(event.target.value); setPage(1) }}><option value="">全部报文</option>{Object.keys(types).sort().map(item => <option key={item}>{item}</option>)}</select></div>
      {error && <div className="notice error">{error}</div>}
      <div className="table-panel"><div className="messages-table-wrap"><table className="messages-table"><thead><tr><th>序号</th><th>时间戳</th><th>阶段</th><th>报文</th><th>方向</th><th>解析内容</th></tr></thead><tbody>{rows.map(row => row.type === 'header' ? <tr key={row.sequence} className="message-divider"><td colSpan="6">{row.content}</td></tr> : <tr key={row.sequence}><td className="muted">{row.sequence}</td><td className="nowrap mono">{row.ts || '—'}</td><td><span className="phase-tag">{row.phase || '其他'}</span></td><td className="strong mono">{row.name || '—'}</td><td className="nowrap muted">{row.direction || '—'}</td><td className="decoded">{row.decoded || '—'}</td></tr>)}{!rows.length && <tr><td colSpan="6" className="table-empty">没有符合条件的报文</td></tr>}</tbody></table></div><div className="table-footer"><span>共 {total.toLocaleString()} 条 · 每页 50 条</span><div className="pagination"><button disabled={page <= 1} onClick={() => setPage(page - 1)}>上一页</button><span>{page} / {pageCount}</span><button disabled={page >= pageCount} onClick={() => setPage(page + 1)}>下一页</button></div></div></div>
    </section><div className="detail-danger"><span>上传于 {formatTime(order.upload_time)}</span></div>
  </>
}

export default function App() {
  const [activeOrder, setActiveOrder] = useState(orderFromPath)
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [uploadOpen, setUploadOpen] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const loadOrders = useCallback(async () => {
    try {
      const data = await request('/api/orders')
      setOrders(data.orders)
      setError('')
    } catch (cause) { setError(cause.message) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { loadOrders() }, [loadOrders])
  useEffect(() => { const handler = () => setActiveOrder(orderFromPath()); window.addEventListener('popstate', handler); return () => window.removeEventListener('popstate', handler) }, [])

  function navigate(orderId) {
    window.history.pushState({}, '', orderId ? `/orders/${encodeURIComponent(orderId)}` : '/')
    setActiveOrder(orderId)
    window.scrollTo(0, 0)
  }

  async function confirmDelete() {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      for (const id of deleteTarget.ids) await request(`/api/orders/${encodeURIComponent(id)}`, { method: 'DELETE' })
      await loadOrders()
      deleteTarget.after?.()
      setDeleteTarget(null)
    } catch (cause) { setError(cause.message); setDeleteTarget(null) }
    finally { setDeleting(false) }
  }

  return <div className="app-shell">
    <aside className="sidebar"><div className="brand"><span className="brand-mark"><Icon name="activity" size={24} /></span><div><strong>充电报文解析</strong><small>GB/T 27930 · 工作台</small></div></div><div className="sidebar-group-label">工作空间</div><button className="nav-item selected" onClick={() => navigate(null)}><Icon name="layers" size={18} /><span>解析工作台</span></button><div className="sidebar-bottom"><div className="sidebar-note"><Icon name="shield" size={19} /><div><strong>本地数据存储</strong><small>原始文件与结果保存在本机</small></div></div><span>GB/T 27930 报文解析</span></div></aside>
    <div className="main-area"><header className="topbar"><div className="breadcrumb"><span>工作空间</span><Icon name="chevron" size={15} /><strong>{activeOrder ? '订单详情' : '解析工作台'}</strong></div><div className="topbar-actions"><span className="local-pill"><span /> 本地运行</span><button className="button primary top-upload" onClick={() => setUploadOpen(true)}><Icon name="upload" size={17} /> 上传报文</button></div></header><main className="content">{activeOrder ? <OrderDetail key={activeOrder} orderId={activeOrder} onBack={() => navigate(null)} /> : <Dashboard orders={orders} loading={loading} error={error} onUpload={() => setUploadOpen(true)} onView={navigate} onDelete={(ids, after) => setDeleteTarget({ ids, after })} />}</main></div>
    {uploadOpen && <UploadDialog orders={orders} onClose={() => setUploadOpen(false)} onUploaded={loadOrders} onOpenOrder={id => { setUploadOpen(false); navigate(id) }} />}
    {deleteTarget && <DeleteDialog count={deleteTarget.ids.length} onClose={() => setDeleteTarget(null)} onConfirm={confirmDelete} busy={deleting} />}
  </div>
}
