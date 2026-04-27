const API_BASE = '/api';
const API_KEY = 'dev-token';

// =====================
// Tab Switching
// =====================
document.querySelectorAll('.command-tab-btn').forEach(btn => {
  btn.addEventListener('click', (e) => {
    const tabName = e.target.dataset.tab;
    switchTab(tabName);
  });
});

function switchTab(tabName) {
  // Hide all tabs
  document.querySelectorAll('.command-tab-content').forEach(tab => {
    tab.classList.remove('active');
  });
  
  // Deactivate all buttons
  document.querySelectorAll('.command-tab-btn').forEach(btn => {
    btn.classList.remove('active');
  });
  
  // Show selected tab
  document.getElementById(tabName + '-tab').classList.add('active');
  document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
  
  // Load initial data when switching tabs
  if (tabName === 'soil') {
    refreshSoilList();
  } else if (tabName === 'plants') {
    loadPlantHistory();
  } else if (tabName === 'status') {
    getSensorStatus();
  }
}

// =====================
// Helper Functions
// =====================
function showStatus(message, isError = false) {
  const el = document.getElementById('status-message');
  el.textContent = message;
  el.style.display = 'block';
  el.style.backgroundColor = isError ? '#ffebee' : '#e8f5e9';
  el.style.color = isError ? '#c62828' : '#2e7d32';
  setTimeout(() => {
    el.style.display = 'none';
  }, 5000);
}

function showResult(elementId, message, isError = false) {
  const el = document.getElementById(elementId);
  el.innerHTML = `<div class="result-box ${isError ? 'error' : 'success'}"><h4>${isError ? 'Error' : 'Success'}</h4><p>${escapeHtml(message)}</p></div>`;
}

function escapeHtml(text) {
  const map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return text.replace(/[&<>"']/g, m => map[m]);
}

async function apiCall(endpoint, method = 'GET', data = null) {
  const options = {
    method,
    headers: {
      'x-api-key': API_KEY,
      'Content-Type': 'application/json',
    },
  };
  
  if (data) {
    options.body = JSON.stringify(data);
  }
  
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, options);
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

// =====================
// Soil Management
// =====================
async function addSoilEntry() {
  const label = document.getElementById('soil-label').value || null;
  const n = parseFloat(document.getElementById('soil-n').value);
  const p = parseFloat(document.getElementById('soil-p').value);
  const k = parseFloat(document.getElementById('soil-k').value);
  const ph = parseFloat(document.getElementById('soil-ph').value);
  const moisture = parseFloat(document.getElementById('soil-moisture').value);
  const temperature = parseFloat(document.getElementById('soil-temperature').value);
  
  if (isNaN(n) || isNaN(p) || isNaN(k) || isNaN(ph) || isNaN(moisture) || isNaN(temperature)) {
    showResult('add-soil-result', 'All soil values are required', true);
    return;
  }
  
  try {
    const result = await apiCall('/commands/soil', 'POST', {
      label, n, p, k, ph, moisture, temperature
    });
    
    showResult('add-soil-result', `Soil entry saved${label ? ` (${label})` : ''}`);
    clearSoilForm();
    refreshSoilList();
  } catch (error) {
    showResult('add-soil-result', error.message, true);
  }
}

function clearSoilForm() {
  document.getElementById('soil-label').value = '';
  document.getElementById('soil-n').value = '';
  document.getElementById('soil-p').value = '';
  document.getElementById('soil-k').value = '';
  document.getElementById('soil-ph').value = '';
  document.getElementById('soil-moisture').value = '';
  document.getElementById('soil-temperature').value = '';
}

async function refreshSoilList() {
  try {
    const result = await apiCall('/commands/soil');
    const list = document.getElementById('soil-list');
    
    if (!result || result.length === 0) {
      list.innerHTML = '<p style="color: #999;">No soil entries saved yet.</p>';
      document.getElementById('check-soil-id').innerHTML = '<option value="">No entries available</option>';
      return;
    }
    
    let html = '';
    let selectHtml = '<option value="">-- Select a soil entry --</option>';
    
    result.forEach(soil => {
      const label = soil.label ? ` (${soil.label})` : '';
      const vals = soil.values;
      const valStr = `N: ${vals[0]}, P: ${vals[1]}, K: ${vals[2]}, pH: ${vals[3]}, Moisture: ${vals[4]}%, Temp: ${vals[5]}°C`;
      
      html += `
        <div class="soil-item">
          <div class="soil-item-info">
            <div class="soil-item-label">Entry #${soil.id}${label}</div>
            <div class="soil-item-values">${escapeHtml(valStr)}</div>
          </div>
          <button class="btn-danger" onclick="deleteSoilEntry(${soil.id})" style="flex-shrink: 0;">Delete</button>
        </div>
      `;
      
      selectHtml += `<option value="${soil.id}">Entry #${soil.id}${label}</option>`;
    });
    
    list.innerHTML = html;
    document.getElementById('check-soil-id').innerHTML = selectHtml;
  } catch (error) {
    document.getElementById('soil-list').innerHTML = `<div class="result-box error"><p>${escapeHtml(error.message)}</p></div>`;
  }
}

async function deleteSoilEntry(soilId) {
  if (!confirm('Delete this soil entry?')) return;
  
  try {
    await apiCall(`/commands/soil/${soilId}`, 'DELETE');
    showStatus('Soil entry deleted');
    refreshSoilList();
  } catch (error) {
    showStatus(error.message, true);
  }
}

async function checkSuitability() {
  const soilId = parseInt(document.getElementById('check-soil-id').value);
  const crop = document.getElementById('check-crop').value;
  
  if (!soilId || !crop) {
    showResult('suitability-result', 'Please select both a soil entry and a crop', true);
    return;
  }
  
  try {
    const result = await apiCall(`/commands/soil/${soilId}/suitability`, 'POST', { crop_name: crop });
    
    const suitable = result.suitable;
    const badge = suitable ? '✅ SUITABLE' : '⚠️ NOT SUITABLE';
    const color = suitable ? 'color: #4caf50;' : 'color: #ff9800;';
    
    let html = `
      <div class="result-box ${suitable ? 'success' : 'error'}">
        <h4 style="${color}">${badge}</h4>
        <p><strong>Crop:</strong> ${escapeHtml(crop)}</p>
        <p><strong>Predicted:</strong> ${escapeHtml(result.predicted)} (${(result.top_prob * 100).toFixed(1)}%)</p>
    `;
    
    if (!suitable && result.procedures && result.procedures.length > 0) {
      html += '<p><strong>Recommendations:</strong><ul>';
      result.procedures.forEach(proc => {
        html += `<li>${escapeHtml(proc)}</li>`;
      });
      html += '</ul></p>';
    }
    
    if (result.alternatives && result.alternatives.length > 0) {
      html += `<p><strong>Alternative crops:</strong> ${result.alternatives.map(c => escapeHtml(c)).join(', ')}</p>`;
    }
    
    html += '</div>';
    document.getElementById('suitability-result').innerHTML = html;
  } catch (error) {
    showResult('suitability-result', error.message, true);
  }
}

// =====================
// Test Crops
// =====================
let testQueue = [];

function addCropTest() {
  const name = document.getElementById('test-crop-name').value.trim();
  const n = parseFloat(document.getElementById('test-n').value);
  const p = parseFloat(document.getElementById('test-p').value);
  const k = parseFloat(document.getElementById('test-k').value);
  const ph = parseFloat(document.getElementById('test-ph').value);
  const moisture = parseFloat(document.getElementById('test-moisture').value);
  const temperature = parseFloat(document.getElementById('test-temperature').value);
  
  if (!name || isNaN(n) || isNaN(p) || isNaN(k) || isNaN(ph) || isNaN(moisture) || isNaN(temperature)) {
    showStatus('All fields are required', true);
    return;
  }
  
  testQueue.push({ name, values: [n, p, k, ph, moisture, temperature] });
  clearTestForm();
  updateTestQueueDisplay();
}

function clearTestForm() {
  document.getElementById('test-crop-name').value = '';
  document.getElementById('test-n').value = '';
  document.getElementById('test-p').value = '';
  document.getElementById('test-k').value = '';
  document.getElementById('test-ph').value = '';
  document.getElementById('test-moisture').value = '';
  document.getElementById('test-temperature').value = '';
}

function clearTestQueue() {
  testQueue = [];
  updateTestQueueDisplay();
  document.getElementById('test-results').innerHTML = '';
}

function updateTestQueueDisplay() {
  const queue = document.getElementById('test-crops-queue');
  
  if (testQueue.length === 0) {
    queue.innerHTML = '<p style="color: #999;">No crops in queue.</p>';
    return;
  }
  
  let html = '<p>Queued crops to test:</p><ul style="margin: 0; padding-left: 20px;">';
  testQueue.forEach((item, idx) => {
    html += `<li>${escapeHtml(item.name)} [N: ${item.values[0]}, P: ${item.values[1]}, K: ${item.values[2]}, pH: ${item.values[3]}, Moisture: ${item.values[4]}, Temp: ${item.values[5]}] <button class="btn-danger" onclick="removeFromQueue(${idx})" style="font-size: 12px; padding: 4px 8px;">Remove</button></li>`;
  });
  html += '</ul>';
  queue.innerHTML = html;
}

function removeFromQueue(index) {
  testQueue.splice(index, 1);
  updateTestQueueDisplay();
}

async function runAllTests() {
  if (testQueue.length === 0) {
    showStatus('Add at least one crop to test', true);
    return;
  }
  
  try {
    const payload = { crops: testQueue };
    const result = await apiCall('/commands/soil/test-crops', 'POST', payload);
    
    let html = '<h4>Test Results</h4>';
    result.results.forEach(r => {
      const suitable = r.suitable;
      const badge = suitable ? '✅ SUITABLE' : '⚠️ NOT SUITABLE';
      const color = suitable ? '#4caf50' : '#ff9800';
      
      if (r.error) {
        html += `<div class="crop-result-item not-suitable" style="color: #f44336;">
          <strong>${escapeHtml(r.crop)}</strong>: Error - ${escapeHtml(r.error)}
        </div>`;
      } else {
        html += `<div class="crop-result-item ${suitable ? 'suitable' : 'not-suitable'}">
          <strong style="color: ${color};">${badge}</strong> ${escapeHtml(r.crop)}<br>
          <span style="font-size: 13px; color: #666;">
            Predicted: ${escapeHtml(r.predicted)} (${(r.confidence * 100).toFixed(1)}%)
          </span>
        </div>`;
      }
    });
    
    document.getElementById('test-results').innerHTML = `<div class="result-box">${html}</div>`;
    testQueue = [];
    updateTestQueueDisplay();
  } catch (error) {
    showStatus(error.message, true);
  }
}

// =====================
// Plant History
// =====================
async function loadPlantHistory() {
  try {
    const result = await apiCall('/commands/plants');
    const container = document.getElementById('plants-current');
    
    let html = '<h4>Current Plant History</h4>';
    
    if (result.previous_plant) {
      html += `<div class="plant-info"><h4>Previous Plant</h4><p>${escapeHtml(result.previous_plant)}</p></div>`;
    } else {
      html += `<div class="plant-info"><h4>Previous Plant</h4><p style="color: #999;">Not set</p></div>`;
    }
    
    if (result.next_plant) {
      html += `<div class="plant-info"><h4>Next Plant</h4><p>${escapeHtml(result.next_plant)}</p></div>`;
    } else {
      html += `<div class="plant-info"><h4>Next Plant</h4><p style="color: #999;">Not set</p></div>`;
    }
    
    container.innerHTML = html;
  } catch (error) {
    document.getElementById('plants-current').innerHTML = `<div class="result-box error">${escapeHtml(error.message)}</div>`;
  }
}

async function setPreviousPlant() {
  const plant = document.getElementById('prev-plant').value.trim();
  if (!plant) {
    showResult('prev-plant-result', 'Plant name is required', true);
    return;
  }
  
  try {
    await apiCall('/commands/plants/previous', 'POST', { plant_name: plant });
    showResult('prev-plant-result', `Previous plant set to: ${plant}`);
    document.getElementById('prev-plant').value = '';
    loadPlantHistory();
  } catch (error) {
    showResult('prev-plant-result', error.message, true);
  }
}

async function setNextPlant() {
  const plant = document.getElementById('next-plant').value.trim();
  if (!plant) {
    showResult('next-plant-result', 'Plant name is required', true);
    return;
  }
  
  try {
    await apiCall('/commands/plants/next', 'POST', { plant_name: plant });
    showResult('next-plant-result', `Next plant set to: ${plant}`);
    document.getElementById('next-plant').value = '';
    loadPlantHistory();
  } catch (error) {
    showResult('next-plant-result', error.message, true);
  }
}

// =====================
// Sensor Status
// =====================
async function getSensorStatus() {
  try {
    const result = await apiCall('/commands/status');
    const container = document.getElementById('sensor-status-result');
    
    if (result.status === 'no_data') {
      container.innerHTML = '<div class="result-box error"><p>No sensor data available yet</p></div>';
      return;
    }
    
    const ts = new Date(result.timestamp).toLocaleString();
    
    let html = `
      <div class="result-box success">
        <h4><span class="status-indicator success"></span>Latest Sensor Reading</h4>
        <table style="width: 100%; font-size: 14px; border-collapse: collapse;">
          <tr>
            <td style="padding: 8px; border-bottom: 1px solid #e0e0e0;">Time:</td>
            <td style="padding: 8px; border-bottom: 1px solid #e0e0e0; font-weight: 600;">${escapeHtml(ts)}</td>
          </tr>
          <tr>
            <td style="padding: 8px; border-bottom: 1px solid #e0e0e0;">Nitrogen (N):</td>
            <td style="padding: 8px; border-bottom: 1px solid #e0e0e0;">${result.np_n !== null ? result.np_n : '—'}</td>
          </tr>
          <tr>
            <td style="padding: 8px; border-bottom: 1px solid #e0e0e0;">Phosphorus (P):</td>
            <td style="padding: 8px; border-bottom: 1px solid #e0e0e0;">${result.np_p !== null ? result.np_p : '—'}</td>
          </tr>
          <tr>
            <td style="padding: 8px; border-bottom: 1px solid #e0e0e0;">Potassium (K):</td>
            <td style="padding: 8px; border-bottom: 1px solid #e0e0e0;">${result.np_k !== null ? result.np_k : '—'}</td>
          </tr>
          <tr>
            <td style="padding: 8px; border-bottom: 1px solid #e0e0e0;">pH:</td>
            <td style="padding: 8px; border-bottom: 1px solid #e0e0e0;">${result.ph !== null ? result.ph : '—'}</td>
          </tr>
          <tr>
            <td style="padding: 8px; border-bottom: 1px solid #e0e0e0;">EC (Electrical Conductivity):</td>
            <td style="padding: 8px; border-bottom: 1px solid #e0e0e0;">${result.ec !== null ? result.ec : '—'}</td>
          </tr>
          <tr>
            <td style="padding: 8px; border-bottom: 1px solid #e0e0e0;">Humidity:</td>
            <td style="padding: 8px; border-bottom: 1px solid #e0e0e0;">${result.humidity !== null ? result.humidity + '%' : '—'}</td>
          </tr>
          <tr>
            <td style="padding: 8px;">Temperature:</td>
            <td style="padding: 8px;">${result.temperature !== null ? result.temperature + '°C' : '—'}</td>
          </tr>
        </table>
      </div>
    `;
    
    container.innerHTML = html;
  } catch (error) {
    document.getElementById('sensor-status-result').innerHTML = `<div class="result-box error"><p>${escapeHtml(error.message)}</p></div>`;
  }
}

// =====================
// Initialize
// =====================
document.addEventListener('DOMContentLoaded', () => {
  refreshSoilList();
});
