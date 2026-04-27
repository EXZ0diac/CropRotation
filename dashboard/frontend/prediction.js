const metaApi = document.querySelector('meta[name="api-base"]')
const API_BASE = (metaApi && metaApi.content) ? metaApi.content.replace(/\/$/, '') : location.origin.replace(/\/$/, '')
const API_KEY = localStorage.getItem('DASHBOARD_API_KEY') || 'dev-token'

async function api(path){
  const res = await fetch(API_BASE + path, { headers: { 'x-api-key': API_KEY } })
  if (!res.ok){
    let msg = await res.text()
    try{
      const parsed = JSON.parse(msg)
      if (parsed && parsed.detail) msg = String(parsed.detail)
    }catch(_e){}
    throw new Error(msg)
  }
  return res.json()
}

function formatValue(value, unit = ''){
  if (value === undefined || value === null) return '—'
  return `${value}${unit ? ` ${unit}` : ''}`
}

function escapeHtml(value){
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function renderTopPredictions(topPredictions){
  if (!Array.isArray(topPredictions) || !topPredictions.length) return '—'
  return topPredictions
    .slice(0, 2)
    .map((item, index) => {
      const percent = Number(item.probability || 0) * 100
      const rank = index === 0 ? 'Top' : 'Runner-up'
      return `<div class="prediction-top-item"><span class="prediction-top-rank">${rank}</span> <span class="crop-pill">${escapeHtml(item.crop || '—')}</span> <span class="prediction-top-prob">${percent.toFixed(2)}%</span></div>`
    })
    .join('')
}

function setStatus(message, isError = false){
  const status = document.getElementById('prediction-status')
  if (!status) return
  status.textContent = message
  status.className = isError ? 'page-status page-status-error' : 'page-status'
}

function renderRows(rows){
  const body = document.getElementById('prediction-table-body')
  const count = document.getElementById('prediction-count')
  const wrap = document.querySelector('.prediction-table-wrap')
  if (!body) return

  // Preserve user scroll position while rows are refreshed every 5 seconds.
  const previousScrollTop = wrap ? wrap.scrollTop : 0

  body.innerHTML = ''
  if (count) count.textContent = `${rows.length} prediction${rows.length === 1 ? '' : 's'}`

  if (!rows.length){
    body.innerHTML = '<tr><td colspan="9">No readings available yet.</td></tr>'
    setStatus('Waiting for sensor readings...')
    return
  }

  rows.forEach(item => {
    const row = document.createElement('tr')
    if (item.error){
      row.innerHTML = `
        <td class="prediction-time">${new Date(item.timestamp).toLocaleString()}</td>
        <td class="prediction-num">${formatValue(item.np_n)}</td>
        <td class="prediction-num">${formatValue(item.np_p)}</td>
        <td class="prediction-num">${formatValue(item.np_k)}</td>
        <td class="prediction-num">${formatValue(item.ph)}</td>
        <td class="prediction-num">${formatValue(item.humidity, '%')}</td>
        <td class="prediction-num">${formatValue(item.temperature, '°C')}</td>
        <td class="prediction-crop-cell" colspan="2">Error: ${escapeHtml(item.error)}</td>
      `
    } else {
      const confidence = Number(item.confidence || 0) * 100
      const confidenceClass = confidence >= 90 ? 'confidence-high' : confidence >= 70 ? 'confidence-medium' : 'confidence-low'
      row.innerHTML = `
        <td class="prediction-time">${new Date(item.timestamp).toLocaleString()}</td>
        <td class="prediction-num">${formatValue(item.np_n)}</td>
        <td class="prediction-num">${formatValue(item.np_p)}</td>
        <td class="prediction-num">${formatValue(item.np_k)}</td>
        <td class="prediction-num">${formatValue(item.ph)}</td>
        <td class="prediction-num">${formatValue(item.humidity, '%')}</td>
        <td class="prediction-num">${formatValue(item.temperature, '°C')}</td>
        <td class="prediction-crop-cell">${renderTopPredictions(item.top_predictions || [])}</td>
        <td class="prediction-confidence-cell"><span class="confidence-pill ${confidenceClass}">${confidence.toFixed(2)}%</span></td>
      `
    }
    body.appendChild(row)
  })

  if (wrap) {
    wrap.scrollTop = previousScrollTop
  }

  setStatus('Auto-updated from the latest 25 readings.')
}

async function refreshPredictionTable(){
  setStatus('Loading prediction results...')
  try{
    const rows = await api('/api/predict/history?limit=25')
    renderRows(rows)
  }catch(e){
    const body = document.getElementById('prediction-table-body')
    if (body){
      body.innerHTML = `<tr><td colspan="9">Error: ${escapeHtml(e.message)}</td></tr>`
    }
    setStatus('Prediction data could not be loaded: ' + e.message, true)
  }
}

refreshPredictionTable()
setInterval(refreshPredictionTable, 5000)
