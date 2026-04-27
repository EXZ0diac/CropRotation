// API base: prefer a meta tag (so you can point the web UI at a remote device like a Raspberry Pi).
// If no meta tag is present, use the page origin (so the UI will call the same host:port serving the page).
const metaApi = document.querySelector('meta[name="api-base"]')
const API_BASE = (metaApi && metaApi.content) ? metaApi.content.replace(/\/$/, '') : location.origin.replace(/\/$/, '')
const API_KEY = localStorage.getItem('DASHBOARD_API_KEY') || 'dev-token'

const METRICS = [
  { key: 'np_n', label: 'Nitrogen', color: '#52c41a', unit: '' },
  { key: 'np_p', label: 'Phosphorus', color: '#fa8c16', unit: '' },
  { key: 'np_k', label: 'Potassium', color: '#13c2c2', unit: '' },
  { key: 'ph', label: 'pH', color: '#2f54eb', unit: '' },
  { key: 'ec', label: 'Electrical Conductivity', color: '#722ed1', unit: 'mS/cm' },
  { key: 'humidity', label: 'Humidity', color: '#1890ff', unit: '%' },
  { key: 'temperature', label: 'Temperature', color: '#ff4d4f', unit: '°C' },
]

async function api(path){
  const url = API_BASE + path
  const res = await fetch(url, {headers:{'x-api-key': API_KEY}})
  if(!res.ok){
    let msg = await res.text()
    try{
      const parsed = JSON.parse(msg)
      if (parsed && parsed.detail) msg = String(parsed.detail)
    }catch(_e){
      // keep raw text
    }
    throw new Error(msg)
  }
  return res.json()
}

async function apiPost(path, payload){
  const url = API_BASE + path
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'x-api-key': API_KEY
    },
    body: JSON.stringify(payload)
  })
  if(!res.ok){
    let msg = await res.text()
    try{
      const parsed = JSON.parse(msg)
      if (parsed && parsed.detail) msg = String(parsed.detail)
    }catch(_e){
      // keep raw text
    }
    throw new Error(msg)
  }
  return res.json()
}

function formatValue(value, unit = ''){
  if (value === undefined || value === null) return '—'
  return `${value}${unit ? ` ${unit}` : ''}`
}

function renderLatest(data){
  const container = document.getElementById('values')
  if (!container) return
  container.innerHTML = ''
  METRICS.forEach(m => {
    const d = document.createElement('div'); d.className='card';
    d.innerHTML = `
      <div class="value-label">${m.label}</div>
      <div class="value-number">${formatValue(data[m.key], m.unit)}</div>
    `
    container.appendChild(d)
  })
}

let charts = {}
function clearChartsGrid(){
  const grid = document.getElementById('charts-grid')
  if (!grid) return
  grid.innerHTML = ''
  charts = {}
}

function createCharts(history){
  const grid = document.getElementById('charts-grid')
  if (!grid) return

  // history expected newest-first; we'll reverse to chronological
  const data = history.slice().reverse()
  const labels = data.map(x => new Date(x.timestamp).toLocaleString())

  clearChartsGrid()

  METRICS.forEach(metric => {
    const card = document.createElement('div')
    card.className = 'chart-card'
    const title = document.createElement('h3')
    title.textContent = metric.label + (metric.unit ? ` (${metric.unit})` : '')
    card.appendChild(title)

    const canvas = document.createElement('canvas')
    canvas.id = 'chart-' + metric.key
    card.appendChild(canvas)
    grid.appendChild(card)

    const values = data.map(x => (x[metric.key] === undefined || x[metric.key] === null) ? null : x[metric.key])

    const ctx = canvas.getContext('2d')
    const ch = new Chart(ctx, {
      type: 'line',
      data: { labels, datasets: [
        { label: metric.label, data: values, borderColor: metric.color, backgroundColor: metric.color, fill: false, tension: 0.2 }
      ] },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: { legend: { display: false } },
        scales: {
          x: { display: true, title: { display: false } },
          y: { display: true }
        }
      }
    })
    charts[metric.key] = ch
  })
}

function renderHistoryTable(history){
  const body = document.getElementById('history-table-body')
  if (!body) return

  body.innerHTML = ''
  history.forEach(item => {
    const row = document.createElement('tr')
    row.innerHTML = `
      <td>${new Date(item.timestamp).toLocaleString()}</td>
      <td>${formatValue(item.np_n)}</td>
      <td>${formatValue(item.np_p)}</td>
      <td>${formatValue(item.np_k)}</td>
      <td>${formatValue(item.ph)}</td>
      <td>${formatValue(item.ec)}</td>
      <td>${formatValue(item.humidity, '%')}</td>
      <td>${formatValue(item.temperature, '°C')}</td>
    `
    body.appendChild(row)
  })
}

function renderPredictionHistory(rows){
  const body = document.getElementById('prediction-table-body')
  if (!body) return

  body.innerHTML = ''
  rows.forEach(item => {
    const row = document.createElement('tr')
    if (item.error){
      row.innerHTML = `
        <td>${new Date(item.timestamp).toLocaleString()}</td>
        <td>${formatValue(item.np_n)}</td>
        <td>${formatValue(item.np_p)}</td>
        <td>${formatValue(item.np_k)}</td>
        <td>${formatValue(item.ph)}</td>
        <td>${formatValue(item.humidity, '%')}</td>
        <td>${formatValue(item.temperature, '°C')}</td>
        <td colspan="2">Error: ${escapeHtml(item.error)}</td>
      `
    }else{
      const confidence = Number(item.confidence || 0) * 100
      row.innerHTML = `
        <td>${new Date(item.timestamp).toLocaleString()}</td>
        <td>${formatValue(item.np_n)}</td>
        <td>${formatValue(item.np_p)}</td>
        <td>${formatValue(item.np_k)}</td>
        <td>${formatValue(item.ph)}</td>
        <td>${formatValue(item.humidity, '%')}</td>
        <td>${formatValue(item.temperature, '°C')}</td>
        <td><strong>${escapeHtml(item.predicted_crop || '—')}</strong></td>
        <td>${confidence.toFixed(2)}%</td>
      `
    }
    body.appendChild(row)
  })
}

function escapeHtml(value){
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function setPredictionInputs(data){
  const n = document.getElementById('pred-n')
  const p = document.getElementById('pred-p')
  const k = document.getElementById('pred-k')
  const ph = document.getElementById('pred-ph')
  const moisture = document.getElementById('pred-moisture')
  const temperature = document.getElementById('pred-temperature')
  if (!n || !p || !k || !ph || !moisture || !temperature) return

  n.value = data.np_n ?? ''
  p.value = data.np_p ?? ''
  k.value = data.np_k ?? ''
  ph.value = data.ph ?? ''
  moisture.value = data.humidity ?? data.moisture ?? ''
  temperature.value = data.temperature ?? ''
}

function renderPredictionResult(data){
  const resultEl = document.getElementById('predict-result')
  if (!resultEl) return

  const confidencePct = Number(data.confidence || 0) * 100
  const topRows = (data.top_predictions || []).map(item => {
    const crop = escapeHtml(item.crop)
    const prob = (Number(item.probability || 0) * 100).toFixed(2)
    return `<li><span>${crop}</span><strong>${prob}%</strong></li>`
  }).join('')

  resultEl.innerHTML = `
    <div class="predict-main">
      <div class="predict-badge">Top Match</div>
      <div class="predict-crop">${escapeHtml(data.predicted_crop || 'Unknown')}</div>
      <div class="predict-confidence">Confidence: ${confidencePct.toFixed(2)}%</div>
    </div>
    <div class="predict-top-list-wrap">
      <div class="predict-top-title">Top Suggestions</div>
      <ul class="predict-top-list">${topRows}</ul>
    </div>
  `
}

function showPredictionError(message){
  const resultEl = document.getElementById('predict-result')
  if (!resultEl) return
  resultEl.innerHTML = `<div class="predict-error">${escapeHtml(message)}</div>`
}

async function useLatestForPrediction(){
  const latest = await api('/api/readings/latest')
  setPredictionInputs(latest)
}

function collectPredictionPayload(){
  const n = Number.parseFloat(document.getElementById('pred-n')?.value || '')
  const p = Number.parseFloat(document.getElementById('pred-p')?.value || '')
  const k = Number.parseFloat(document.getElementById('pred-k')?.value || '')
  const ph = Number.parseFloat(document.getElementById('pred-ph')?.value || '')
  const moisture = Number.parseFloat(document.getElementById('pred-moisture')?.value || '')
  const temperature = Number.parseFloat(document.getElementById('pred-temperature')?.value || '')

  const values = [n, p, k, ph, moisture, temperature]
  const hasInvalid = values.some(v => !Number.isFinite(v))
  if (hasInvalid){
    throw new Error('Please provide valid numeric values for all fields.')
  }

  return {
    np_n: n,
    np_p: p,
    np_k: k,
    ph,
    moisture,
    temperature,
  }
}

function initPredictionUI(){
  const form = document.getElementById('predict-form')
  const latestBtn = document.getElementById('use-latest-btn')
  if (!form) return

  if (latestBtn){
    latestBtn.addEventListener('click', async () => {
      try{
        await useLatestForPrediction()
      }catch(e){
        showPredictionError('Failed to load latest reading: ' + e.message)
      }
    })
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault()
    try{
      const payload = collectPredictionPayload()
      const prediction = await apiPost('/api/predict', payload)
      renderPredictionResult(prediction)
    }catch(e){
      showPredictionError('Prediction failed: ' + e.message)
    }
  })

  const resultEl = document.getElementById('predict-result')
  if (resultEl && resultEl.classList.contains('predict-result-empty')){
    useLatestForPrediction().catch(() => {
      // Keep initial empty state when no latest reading exists.
    })
  }
}

async function refresh(){
  try{
    const hasLatestCards = !!document.getElementById('values')
    const hasCharts = !!document.getElementById('charts-grid')
    const hasHistoryTable = !!document.getElementById('history-table-body')
    const hasPredictionHistory = !!document.getElementById('prediction-table-body')

    if (hasLatestCards){
      const latest = await api('/api/readings/latest')
      renderLatest(latest)
    }

    if (hasCharts){
      const history = await api('/api/readings/history?limit=100')
      createCharts(history)
    }

    if (hasHistoryTable){
      const history = await api('/api/readings/history?limit=50')
      renderHistoryTable(history)
    }

    if (hasPredictionHistory){
      const predictions = await api('/api/predict/history?limit=10')
      renderPredictionHistory(predictions)
    }
  }catch(e){
    console.error(e)
    const values = document.getElementById('values')
    if (values) values.innerText = 'Error: ' + e.message
    const body = document.getElementById('history-table-body')
    if (body) {
      body.innerHTML = `<tr><td colspan="8">Error: ${e.message}</td></tr>`
    }
    const predictionBody = document.getElementById('prediction-table-body')
    if (predictionBody){
      predictionBody.innerHTML = `<tr><td colspan="9">Error: ${e.message}</td></tr>`
    }
  }
}

// refresh periodically
// refresh periodically and open SSE stream to receive live updates
// Refresh the full page data every 5 seconds for testing
setInterval(refresh, 5000)
refresh()
initPredictionUI()

// Setup Server-Sent Events to receive live readings and update charts without page reload
function startSSE(){
  if (!document.getElementById('values') && !document.getElementById('charts-grid')) {
    return
  }
  if (typeof EventSource === 'undefined') return
  // EventSource can't set custom headers, so include the API key as a query
  // parameter which the server accepts for SSE connections.
  const sseUrl = API_BASE + '/api/stream' + (API_KEY ? ('?api_key=' + encodeURIComponent(API_KEY)) : '')
  // Log the exact SSE URL so you can verify the API key is present in the browser
  // (open DevTools Console to inspect). This helps debug 401/403 SSE issues.
  console.log('SSE URL ->', sseUrl)
  const es = new EventSource(sseUrl, { withCredentials: false })
  es.onmessage = function(evt){
    try{
      const data = JSON.parse(evt.data)
      // update latest values
      renderLatest(data)
      // append to each chart dataset
      const tsLabel = new Date(data.timestamp).toLocaleString()
      METRICS.forEach(m => {
        const ch = charts[m.key]
        if (!ch) return
        // push label and value
        ch.data.labels.push(tsLabel)
        ch.data.datasets[0].data.push(data[m.key] === undefined ? null : data[m.key])
        // trim to 100 points
        if (ch.data.labels.length > 100){
          ch.data.labels.shift()
          ch.data.datasets[0].data.shift()
        }
        ch.update('none')
      })
    }catch(e){
      console.error('SSE parse error', e)
    }
  }
  es.onerror = function(e){
    console.warn('SSE connection error', e)
    // close and try reconnect later
    es.close()
    setTimeout(startSSE, 5000)
  }
}

// start SSE after initial load
setTimeout(startSSE, 1000)
