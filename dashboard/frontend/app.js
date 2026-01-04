// API base: prefer a meta tag (so you can point the web UI at a remote device like a Raspberry Pi).
// If no meta tag is present, use the page origin (so the UI will call the same host:port serving the page).
const metaApi = document.querySelector('meta[name="api-base"]')
const API_BASE = (metaApi && metaApi.content) ? metaApi.content.replace(/\/$/, '') : location.origin.replace(/\/$/, '')
const API_KEY = localStorage.getItem('DASHBOARD_API_KEY') || 'dev-token'

const METRICS = [
  { key: 'np_n', label: 'N', color: '#52c41a', unit: '' },
  { key: 'np_p', label: 'P', color: '#fa8c16', unit: '' },
  { key: 'np_k', label: 'K', color: '#13c2c2', unit: '' },
  { key: 'ph', label: 'pH', color: '#2f54eb', unit: '' },
  { key: 'ec', label: 'EC', color: '#722ed1', unit: 'mS/cm' },
  { key: 'humidity', label: 'Humidity', color: '#1890ff', unit: '%' },
  { key: 'temperature', label: 'Temperature', color: '#ff4d4f', unit: '°C' },
]

async function api(path){
  const url = API_BASE + path
  const res = await fetch(url, {headers:{'x-api-key': API_KEY}})
  if(!res.ok) throw new Error(await res.text())
  return res.json()
}

function renderLatest(data){
  const container = document.getElementById('values')
  container.innerHTML = ''
  METRICS.forEach(m => {
    const d = document.createElement('div'); d.className='card';
    d.innerHTML = `
      <div class="value-label">${m.label}</div>
      <div class="value-number">${(data[m.key] !== undefined && data[m.key] !== null) ? data[m.key] : '—'} ${m.unit}</div>
    `
    container.appendChild(d)
  })
}

let charts = {}
function clearChartsGrid(){
  const grid = document.getElementById('charts-grid')
  grid.innerHTML = ''
  charts = {}
}

function createCharts(history){
  // history expected newest-first; we'll reverse to chronological
  const data = history.slice().reverse()
  const labels = data.map(x => new Date(x.timestamp).toLocaleString())

  const grid = document.getElementById('charts-grid')
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

async function refresh(){
  try{
    const latest = await api('/api/readings/latest')
    renderLatest(latest)
    const history = await api('/api/readings/history?limit=100')
    createCharts(history)
  }catch(e){
    console.error(e)
    document.getElementById('values').innerText = 'Error: '+e.message
  }
}

// refresh periodically
// refresh periodically and open SSE stream to receive live updates
// Refresh the full page data every 60 seconds (1 minute)
setInterval(refresh, 60000)
refresh()

// Setup Server-Sent Events to receive live readings and update charts without page reload
function startSSE(){
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
