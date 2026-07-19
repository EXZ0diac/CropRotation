const API_BASE = '/api';
const API_KEY = 'dev-token';

// =====================
// Crop Preparation Information
// =====================
const CROP_PREPARATION = {
  "Chili": {
    "description": "Hot peppers - good for dried chili production",
    "preparation": [
      "Prepare seedbeds 3-4 weeks before planting",
      "Maintain soil temperature at 25-30°C for germination",
      "Harden seedlings for 1 week before transplanting",
      "Space plants 45-60cm apart",
      "Install support stakes for tall varieties",
      "Provide drip irrigation for consistent watering",
      "Apply mulch to retain moisture",
      "Use netting for bird protection if needed"
    ],
    "planting_season": "Year-round in Malaysia (prefer March-April or August-September)",
    "harvest_days": "75-90 days from transplanting"
  },
  "Cucumber": {
    "description": "Cucurbitaceae family - high water content vegetable",
    "preparation": [
      "Create raised beds or mounds for drainage",
      "Direct sow seeds or transplant 3-week old seedlings",
      "Maintain soil moisture at 60-90%",
      "Build trellises for vertical growth to save space",
      "Apply mulch around plants",
      "Feed with balanced fertilizer every 2 weeks",
      "Ensure proper air circulation to prevent fungal diseases",
      "Install shade cloth during extreme heat (>35°C)"
    ],
    "planting_season": "January-March, August-October",
    "harvest_days": "50-70 days from seeding"
  },
  "Groundnut": {
    "description": "Legume crop - nitrogen-fixing, good for soil health",
    "preparation": [
      "Remove soil compaction through deep plowing",
      "Ensure well-draining soil (pH 5.5-6.5)",
      "Sow seeds directly in furrows 5-6cm deep",
      "Space seeds 10-15cm apart, rows 45cm apart",
      "Apply rhizobia inoculant if new to growing groundnuts",
      "Avoid waterlogging - groundnuts are sensitive to excess moisture",
      "Minimal fertilizer needed due to nitrogen fixation",
      "Mulch lightly to retain soil moisture"
    ],
    "planting_season": "March-April, September-October",
    "harvest_days": "90-120 days from seeding"
  },
  "Maize": {
    "description": "Staple cereal crop - high yielding",
    "preparation": [
      "Plow field deeply (25-30cm) and level",
      "Apply compost or manure 2-3 weeks before planting",
      "Create furrows 60-80cm apart",
      "Sow seeds at 2cm depth, 1-2 seeds per hill",
      "Thin to 1 plant per hill after germination",
      "Space hills 20-25cm apart within rows",
      "Top-dress with nitrogen at 4-6 leaf stage",
      "Install support if growing tall varieties"
    ],
    "planting_season": "March-April, June-July, October-November",
    "harvest_days": "70-90 days from seeding"
  },
  "Paddy": {
    "description": "Wetland rice - requires flooded conditions",
    "preparation": [
      "Prepare nursery beds 30 days before planting",
      "Puddle the field to desired texture (5-8cm soft mud)",
      "Ensure proper water management system",
      "Level the field to 2-5cm water depth",
      "Transplant 30-40 day old seedlings",
      "Space seedlings 15-20cm apart in rows 20-25cm apart",
      "Maintain flood level at 5-8cm during growing season",
      "Drain field 15 days before harvest",
      "Install water gates for flow control"
    ],
    "planting_season": "April-May (monsoon), September-October (dry season)",
    "harvest_days": "100-120 days from transplanting"
  },
  "Spinach": {
    "description": "Leafy green vegetable - high nutrient content",
    "preparation": [
      "Add compost or organic matter before planting",
      "Create rows 30cm apart",
      "Direct sow seeds in furrows 1-2cm deep",
      "Thin seedlings to 10-15cm apart",
      "Keep soil consistently moist (avoid waterlogging)",
      "Apply balanced fertilizer at planting and again after 3 weeks",
      "Provide partial shade in hot seasons (>28°C)",
      "Harvest outer leaves regularly to encourage growth",
      "Plant in cool season for best quality (Oct-Feb in Malaysia)"
    ],
    "planting_season": "October-February (preferred), year-round possible",
    "harvest_days": "40-60 days from seeding"
  },
  "Tomato": {
    "description": "Solanaceae family - versatile fruit vegetable",
    "preparation": [
      "Start seeds indoors 6-8 weeks before transplanting",
      "Prepare soil with plenty of organic matter",
      "Build trellises or support cages",
      "Harden seedlings for 1 week before transplanting",
      "Space plants 60-90cm apart (indeterminate varieties)",
      "Install drip irrigation system",
      "Mulch around plants (5-8cm depth)",
      "Prune suckers for better fruit production",
      "Apply fungicide regularly in humid conditions"
    ],
    "planting_season": "December-January, May-June (avoid monsoon)",
    "harvest_days": "60-85 days from transplanting"
  },
  "Eggplant": {
    "description": "Solanaceae family - tropical crop with high yield",
    "preparation": [
      "Start seeds in nursery 5-6 weeks before transplanting",
      "Prepare raised beds for better drainage",
      "Space plants 60-75cm apart in rows",
      "Install sturdy stakes for support",
      "Maintain consistent soil moisture",
      "Apply thick mulch (5-8cm) to retain moisture",
      "Prune lower branches for air circulation",
      "Scout regularly for pests (fruit borer, whiteflies)",
      "Hand-pick fruits when 2/3 mature for best quality"
    ],
    "planting_season": "March-April, August-September",
    "harvest_days": "55-70 days from transplanting"
  },
  "Okra": {
    "description": "Malvaceae family - heat-loving crop, sticky vegetables",
    "preparation": [
      "Direct sow seeds after last frost/cold spell",
      "Soak seeds overnight for faster germination",
      "Plant in rows 60-75cm apart",
      "Space seeds 30-45cm apart",
      "Ensure well-draining soil",
      "Apply nitrogen fertilizer monthly",
      "Provide light mulching",
      "No special support needed for dwarf varieties",
      "Harvest pods every 2-3 days when 5-8cm long"
    ],
    "planting_season": "April-June, October-November",
    "harvest_days": "50-65 days from seeding"
  },
  "Bitter Gourd": {
    "description": "Cucurbitaceae family - climbing vine with bitter fruits",
    "preparation": [
      "Build strong trellises or pergolas (2-3m height)",
      "Prepare soil rich in organic matter",
      "Direct sow seeds or transplant seedlings",
      "Space plants 45-60cm apart",
      "Thin to 1 plant per hill",
      "Train vines on trellises as they grow",
      "Apply mulch around base",
      "Provide adequate moisture during flowering",
      "Harvest when fruits are green (before turning yellow)"
    ],
    "planting_season": "March-April, August-September",
    "harvest_days": "60-75 days from seeding"
  },
  "Pumpkin": {
    "description": "Cucurbitaceae family - vine crop with large fruits",
    "preparation": [
      "Prepare ground with deep soil cultivation",
      "Create hills or mounds 60cm apart",
      "Plant 2-3 seeds per hill",
      "Thin to 1-2 plants per hill after germination",
      "Keep field weed-free for first 6-8 weeks",
      "Apply thick mulch (5-8cm) to retain moisture",
      "Prune runners if space is limited",
      "Support developing fruits with straw",
      "Ensure consistent watering during flowering and fruit development"
    ],
    "planting_season": "April-May, September-October",
    "harvest_days": "80-120 days from seeding (depending on variety)"
  },
  "Brinjal": {
    "description": "Solanaceae family - tropical version of eggplant",
    "preparation": [
      "Start seeds in nursery 6-8 weeks before planting",
      "Harden seedlings for 1 week",
      "Prepare raised beds for drainage",
      "Space plants 60cm apart each way",
      "Install bamboo or wooden stakes for support",
      "Tie plants gently to supports",
      "Apply organic mulch (5cm depth)",
      "Feed with nitrogen every 3-4 weeks",
      "Remove first flowering for better plant development"
    ],
    "planting_season": "March-April, August-September",
    "harvest_days": "60-75 days from transplanting"
  }
};

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
  // Stop any tab-specific background tasks (e.g., sensor polling)
  stopSensorPolling();

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
  } else if (tabName === 'test') {
    refreshTestSoilList();
  } else if (tabName === 'plants') {
    loadPlantHistory();
  } else if (tabName === 'status') {
    startSensorPolling();
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
// Sensor polling (live updates)
// =====================
let sensorPollId = null;
const SENSOR_POLL_INTERVAL_MS = 5000; // 5 seconds

function startSensorPolling() {
  if (sensorPollId) return; // already running
  // fetch immediately then schedule
  getSensorStatus();
  sensorPollId = setInterval(() => {
    getSensorStatus().catch(() => {});
  }, SENSOR_POLL_INTERVAL_MS);
}

function stopSensorPolling() {
  if (!sensorPollId) return;
  clearInterval(sensorPollId);
  sensorPollId = null;
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
      return;
    }
    
    let html = '';
    
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
    });
    
    list.innerHTML = html;
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

// =====================
// Test Crops
// =====================

async function refreshTestSoilList() {
  try {
    const result = await apiCall('/commands/soil');
    
    if (!result || result.length === 0) {
      document.getElementById('test-soil-entry').innerHTML = '<option value="">No soil entries available</option>';
      return;
    }
    
    let selectHtml = '<option value="">-- Select a soil entry --</option>';
    result.forEach(soil => {
      const label = soil.label ? ` (${soil.label})` : '';
      selectHtml += `<option value="${soil.id}">Entry #${soil.id}${label}</option>`;
    });
    
    document.getElementById('test-soil-entry').innerHTML = selectHtml;
  } catch (error) {
    document.getElementById('test-soil-entry').innerHTML = `<option value="">Error loading soil entries</option>`;
  }
}

async function testAllCropsBySoil() {
  const soilId = parseInt(document.getElementById('test-soil-entry').value);
  
  if (!soilId) {
    showStatus('Please select a soil entry to test', true);
    return;
  }
  
  try {
    const result = await apiCall(`/commands/soil/${soilId}/all-suitable-crops`, 'GET');
    
    let html = `<div class="result-box">`;
    
    // Show soil info
    html += `<div style="margin-bottom: 20px; padding: 12px; background-color: #f5f5f5; border-radius: 4px;">
      <strong>Soil Entry:</strong> ${result.soil_label ? `${result.soil_label} (Entry #${result.soil_id})` : `Entry #${result.soil_id}`}<br>
      <small style="color: #666;">N: ${result.soil_values.N.toFixed(1)}, P: ${result.soil_values.P.toFixed(1)}, K: ${result.soil_values.K.toFixed(1)}, pH: ${result.soil_values.pH.toFixed(1)}, Moisture: ${result.soil_values.Moisture.toFixed(1)}%, Temp: ${result.soil_values.Temperature.toFixed(1)}°C</small>
    </div>`;
    
    // If no suitable crops, show soil treatment at the top
    if (!result.suitable_crops || result.suitable_crops.length === 0) {
      html += `<div style="margin-bottom: 24px; padding: 14px; background-color: #fff9c4; border-left: 4px solid #fbc02d; border-radius: 4px;">
        <strong style="color: #f57f17; font-size: 14px;">🌱 Soil Treatment Recommendation</strong><br>
        <p style="color: #555; font-size: 13px; margin: 8px 0;">Your soil needs adjustments to support most crops. Consider:</p>
        <ul style="margin: 8px 0; padding-left: 20px; font-size: 13px; color: #555;">
          <li>Conduct a soil test to identify deficiencies</li>
          <li>Add organic matter and compost to improve soil structure</li>
          <li>Adjust pH levels if needed (use lime or sulfur)</li>
          <li>Balance nutrient levels (N, P, K) with appropriate fertilizers</li>
          <li>Improve soil drainage and moisture retention</li>
          <li>Wait 2-3 weeks after treatment before planting</li>
        </ul>
        <p style="color: #f57f17; font-size: 12px; margin-top: 8px;"><strong>After treatment:</strong> Re-check suitability to see which crops become viable.</p>
      </div>`;
    }
    
    // Display suitable crops
    if (result.suitable_crops && result.suitable_crops.length > 0) {
      html += `<h4 style="color: #4caf50; margin-top: 0;">✅ Suitable Crops (${result.suitable_crops.length})</h4>`;
      result.suitable_crops.forEach(crop => {
        html += `
          <div style="margin-bottom: 16px; padding: 12px; background-color: #e8f5e9; border-left: 4px solid #4caf50; border-radius: 4px;">
            <strong style="color: #2e7d32; font-size: 16px;">${escapeHtml(crop.crop_name)}</strong><br>
            <span style="color: #555;">Confidence: ${(crop.top_prob * 100).toFixed(1)}%</span>
        `;
        
        // Show why it's suitable
        if (crop.analysis && crop.analysis.matched) {
          html += `<br><strong style="color: #2e7d32; font-size: 12px;">Why it's suitable:</strong><ul style="margin: 6px 0; padding-left: 20px; font-size: 13px;">`;
          crop.analysis.matched.forEach(param => {
            html += `<li style="color: #2e7d32;">${escapeHtml(param)}</li>`;
          });
          html += `</ul>`;
        }
        
        html += `</div>`;
      });
    } else {
      html += `<p style="color: #ff9800; font-size: 14px; padding: 12px; background-color: #fff3e0; border-radius: 4px; margin-top: 12px;">⚠️ No suitable crops found for this soil. Consider alternatives below or apply soil treatments above.</p>`;
    }
    
    // Display unsuitable crops with detailed analysis
    if (result.unsuitable_crops && result.unsuitable_crops.length > 0) {
      html += `<h4 style="color: #ff9800; margin-top: 24px;">⚠️ Unsuitable Crops (${result.unsuitable_crops.length})</h4>`;
      result.unsuitable_crops.forEach(crop => {
        html += `
          <div style="margin-bottom: 16px; padding: 12px; background-color: #fff3e0; border-left: 4px solid #ff9800; border-radius: 4px;">
            <strong style="color: #e65100; font-size: 14px;">${escapeHtml(crop.crop_name)}</strong><br>
            <span style="color: #555; font-size: 13px;">Confidence: ${(crop.top_prob * 100).toFixed(1)}%</span>
        `;
        
        // Show why it's unsuitable
        if (crop.analysis && crop.analysis.unmatched && crop.analysis.unmatched.length > 0) {
          html += `<br><strong style="color: #e65100; font-size: 12px;">Why it's unsuitable:</strong><ul style="margin: 6px 0; padding-left: 20px; font-size: 13px;">`;
          crop.analysis.unmatched.forEach(param => {
            html += `<li style="color: #d84315;">${escapeHtml(param)}</li>`;
          });
          html += `</ul>`;
        }
        
        // Show adjustments needed
        if (crop.procedures && crop.procedures.length > 0) {
          html += `<br><strong style="color: #e65100; font-size: 12px;">To make it suitable, adjust:</strong><ul style="margin: 6px 0; padding-left: 20px; font-size: 13px;">`;
          crop.procedures.forEach(proc => {
            html += `<li>${escapeHtml(proc)}</li>`;
          });
          html += `</ul>`;
        }
        
        html += `</div>`;
      });
    }
    
    // Display alternative crops
    if (result.alternative_crops && result.alternative_crops.length > 0) {
      html += `<h4 style="color: #2196F3; margin-top: 24px;">💡 Alternative Crop Options</h4>`;
      result.alternative_crops.forEach(crop => {
        html += `
          <div style="margin-bottom: 12px; padding: 12px; background-color: #e3f2fd; border-left: 4px solid #2196F3; border-radius: 4px;">
            <strong style="color: #1976d2; font-size: 14px;">${escapeHtml(crop.crop)}</strong>
            <span style="color: #1976d2; font-size: 13px;"> - ${crop.matched_params}/${6} soil parameters match</span>
            <br><span style="color: #1565c0; font-size: 12px;">Match: ${crop.match_percentage.toFixed(0)}% | This crop can work well with your current soil conditions.</span>
          </div>
        `;
      });
    }
    
    html += `</div>`;
    document.getElementById('test-results').innerHTML = html;
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
      const fieldDisplay = result.previous_field ? ` <span style="color: #666; font-size: 12px;">(${escapeHtml(result.previous_field)})</span>` : '';
      html += `<div class="plant-info"><h4>Previous Plant</h4><p>${escapeHtml(result.previous_plant)}${fieldDisplay}</p></div>`;
    } else {
      html += `<div class="plant-info"><h4>Previous Plant</h4><p style="color: #999;">Not set</p></div>`;
    }
    
    if (result.next_plant) {
      const fieldDisplay = result.next_field ? ` <span style="color: #666; font-size: 12px;">(${escapeHtml(result.next_field)})</span>` : '';
      html += `<div class="plant-info"><h4>Next Plant</h4><p>${escapeHtml(result.next_plant)}${fieldDisplay}</p></div>`;
    } else {
      html += `<div class="plant-info"><h4>Next Plant</h4><p style="color: #999;">Not set</p></div>`;
    }
    
    container.innerHTML = html;
  } catch (error) {
    document.getElementById('plants-current').innerHTML = `<div class="result-box error">${escapeHtml(error.message)}</div>`;
  }
}

async function setNextPlant() {
  const plant = document.getElementById('next-plant').value.trim();
  const field = document.getElementById('next-plant-field').value.trim();
  
  if (!plant) {
    showStatus('Please select a crop', true);
    return;
  }
  
  if (!field) {
    showStatus('Please select a field', true);
    return;
  }
  
  try {
    await apiCall('/commands/plants/next', 'POST', { 
      plant_name: plant,
      field_name: field
    });
    
    showStatus(`✅ Next plant set to: ${plant} in ${field}`);
    
    // Display preparation information
    displayPlantPreparation(plant);
    
    // Reload plant history
    loadPlantHistory();
    document.getElementById('next-plant').value = '';
    document.getElementById('next-plant-field').value = '';
  } catch (error) {
    showStatus(error.message, true);
  }
}

function displayPlantPreparation(cropName) {
  const prep = CROP_PREPARATION[cropName];
  if (!prep) {
    document.getElementById('plant-preparation').innerHTML = '';
    return;
  }
  
  let html = `<div class="command-form" style="margin-top: 20px;">
    <h4 style="color: #2196F3;">📋 Preparation Guide for ${escapeHtml(cropName)}</h4>
    <p style="color: #555; font-size: 13px; margin: 8px 0;"><strong>${escapeHtml(prep.description)}</strong></p>
    
    <div style="margin-bottom: 16px; padding: 12px; background-color: #e3f2fd; border-radius: 4px;">
      <strong style="color: #1565c0; font-size: 13px;">📅 Planting Season:</strong>
      <p style="color: #555; font-size: 13px; margin: 4px 0;">${escapeHtml(prep.planting_season)}</p>
      
      <strong style="color: #1565c0; font-size: 13px;">⏱️ Days to Harvest:</strong>
      <p style="color: #555; font-size: 13px; margin: 4px 0;">${escapeHtml(prep.harvest_days)}</p>
    </div>
    
    <strong style="color: #1565c0; font-size: 13px;">🌱 Preparation Steps:</strong>
    <ul style="margin: 8px 0; padding-left: 20px; font-size: 13px;">
  `;
  
  prep.preparation.forEach(step => {
    html += `<li style="color: #555; margin: 4px 0;">${escapeHtml(step)}</li>`;
  });
  
  html += `</ul></div>`;
  document.getElementById('plant-preparation').innerHTML = html;
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
    
    // Parse timestamp robustly and display in Malaysia timezone
    let tsDate;
    try {
      if (typeof result.timestamp === 'number') {
        tsDate = new Date(result.timestamp);
      } else {
        const tsStr = String(result.timestamp || '');
        // If timestamp looks like an ISO string without timezone info, treat it as UTC
        const isoNoTZ = /\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?$/;
        if (isoNoTZ.test(tsStr)) {
          tsDate = new Date(tsStr + 'Z');
        } else {
          tsDate = new Date(tsStr);
        }
      }
    } catch (e) {
      tsDate = new Date();
    }

    // Format using Malaysia timezone so UI follows local Malaysia time
    const ts = tsDate.toLocaleString('en-GB', { timeZone: 'Asia/Kuala_Lumpur' });
    
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
