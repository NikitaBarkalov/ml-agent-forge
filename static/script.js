/**
 * ML Agent Forge - Frontend
 * Handles file upload, WebSocket run, live logs, and downloads.
 */

const API_BASE = '';

// DOM elements
const form = document.getElementById('run-form');
const runBtn = document.getElementById('run-btn');
const fileInput = document.getElementById('file-input');
const fileNameSpan = document.getElementById('file-name');
const statusValue = document.getElementById('status-value');
const logContent = document.getElementById('log-content');
const progressSection = document.getElementById('progress-section');
const resultsSection = document.getElementById('results-section');
const downloadsDiv = document.getElementById('downloads');

let uploadedPath = null;
let lastActiveAgent = null; // Track the last highlighted agent to prevent unnecessary re-renders

const SCENARIOS = {
  ba: {
    context: "We are an e-commerce company planning to expand our product line into high-end sustainable furniture. We currently sell standard office supplies and electronics.",
    task: "Analyze our current sales trends by region and product category. Based on the performance of our 'Furniture' category in the South and West regions, suggest 3 specific sustainable furniture products we should launch next quarter.",
    file: "sales_data.csv"
  },
  da: {
    context: "The management team wants a deep dive into our profit margins across different regions and product types.",
    task: "Perform an exploratory data analysis (EDA) to identify which product category is most profitable per unit. Create a visualization showing the profit distribution by region. Highlight any regions where sales are high but profit is low.",
    file: "sales_data.csv"
  },
  ml: {
    context: "We want to optimize our inventory by predicting future sales volume.",
    task: "Build a simple time-series forecasting model (or a regression model using date as a feature) to predict the total sales volume for the next 7 days. Use the existing data for training and evaluation. Print the Mean Absolute Error (MAE) and save a plot of historical vs. predicted sales.",
    file: "sales_data.csv"
  }
};

// Scenario selection
const scenarioSelect = document.getElementById('scenario-select');
scenarioSelect.addEventListener('change', () => {
  const key = scenarioSelect.value;
  if (key && SCENARIOS[key]) {
    document.getElementById('business-context').value = SCENARIOS[key].context;
    document.getElementById('task').value = SCENARIOS[key].task;

    if (!uploadedPath) {
      fileNameSpan.textContent = `Please upload ${SCENARIOS[key].file}`;
      fileNameSpan.classList.add('warning');
    }
  }
});

// File selection
fileInput.addEventListener('change', () => {
  const file = fileInput.files[0];
  if (file) {
    fileNameSpan.textContent = file.name;
    uploadFile(file);
  } else {
    fileNameSpan.textContent = 'No file selected';
    uploadedPath = null;
  }
});

async function uploadFile(file) {
  const fd = new FormData();
  fd.append('file', file);
  try {
    const r = await fetch(`${API_BASE}/upload`, { method: 'POST', body: fd });
    const data = await r.json();
    uploadedPath = data.filename;
    fileNameSpan.textContent = `${file.name} (uploaded)`;
  } catch (e) {
    fileNameSpan.textContent = `Upload failed: ${e.message}`;
    uploadedPath = null;
  }
}

function appendLog(ev) {
  const pre = logContent;
  const line = document.createElement('div');
  line.className = 'log-line';

  const ts = ev.timestamp ? new Date(ev.timestamp).toLocaleTimeString() : '';
  const agent = ev.agent ? `[${ev.agent}]` : '';
  const msg = ev.message || JSON.stringify(ev);
  const level = ev.level || 'info';

  line.innerHTML = `<span class="ts">${ts}</span> <span class="agent">${agent}</span> <span class="level-${level}">${msg}</span>`;
  pre.appendChild(line);
  const logWindow = document.getElementById('log-window');
  if (logWindow) logWindow.scrollTop = logWindow.scrollHeight;
}

function setStatus(text, className = '') {
  statusValue.textContent = text;
  statusValue.className = 'status-value ' + className;
}

function showResults(downloads) {
  resultsSection.classList.remove('hidden');
  downloadsDiv.innerHTML = '';
  if (downloads.report) {
    const btn = document.createElement('button');
    btn.className = 'btn';
    btn.textContent = 'Download Report (.md)';
    btn.onclick = () => window.open(`${API_BASE}/download/${downloads.report}`, '_blank');
    downloadsDiv.appendChild(btn);
  }
  if (downloads.pipeline) {
    const btn = document.createElement('button');
    btn.className = 'btn';
    btn.textContent = 'Download Code / Pipeline';
    btn.onclick = () => window.open(`${API_BASE}/download/${downloads.pipeline}`, '_blank');
    downloadsDiv.appendChild(btn);
  }
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();

  const businessContext = document.getElementById('business-context').value.trim();
  const task = document.getElementById('task').value.trim();
  const filePaths = uploadedPath ? [uploadedPath] : [];

  runBtn.disabled = true;
  setStatus('Connecting...', 'running');
  logContent.innerHTML = '';
  
  // Reset the graph state on new run
  lastActiveAgent = null; 
  highlightAgent(null);

  const wsUrl = `${(window.location.protocol === 'https:' ? 'wss:' : 'ws:')}//${window.location.host}${API_BASE}/ws/run`;
  const ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    setStatus('Running pipeline...', 'running');
    ws.send(JSON.stringify({
      business_context: businessContext,
      task,
      file_paths: filePaths,
    }));
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);

      if (data.type === 'log') {
        appendLog(data);
        if (data.agent) {
          if (data.message && data.message.includes('Agent started')) {
             setStatus(`Current Step: ${data.agent}`, 'running');
          }
          // Highlight ONLY if the agent has changed (performance fix)
          highlightAgent(data.agent);

          if (data.reason && typeof showReasoning === 'function') {
              showReasoning(data.agent, data.reason);
          }
        }
      } else if (data.type === 'done') {
        setStatus('Done', 'done');
        showResults(data.downloads || {});
        
        // Highlight ALL agents at the end to show completion
        highlightAgent('ALL'); 
        
        runBtn.disabled = false;
      } else if (data.type === 'error') {
        setStatus(`Error: ${data.message}`, 'error');
        appendLog({ message: data.message, level: 'error' });
        runBtn.disabled = false;
      }
    } catch (e) {
      console.error(e); 
      appendLog({ message: event.data, level: 'info' });
    }
  };

  ws.onerror = () => {
    setStatus('Connection error', 'error');
    runBtn.disabled = false;
  };

  ws.onclose = () => {
    if (runBtn.disabled && statusValue.textContent.includes('Running')) {
      setStatus('Connection closed', 'error');
      runBtn.disabled = false;
    }
  };
});

function highlightAgent(agentName) {
    const safeAgent = agentName ? agentName.trim() : '';
    
    // Performance Check: Don't re-render mermaid if the state hasn't changed.
    if (safeAgent === lastActiveAgent) {
        return;
    }
    
    lastActiveAgent = safeAgent;
    updateGraphUI(safeAgent); 
}

async function updateGraphUI(activeAgent) {
    const element = document.getElementById('agent-graph');
    if (!element) return;
    
    // Graph Definition for Mermaid
    // FIX: Changed "Detective[DataDetective]" to "DataDetective" to match backend names.
    let graphDefinition = `
    graph TD
        %% Define nodes and edges
        Start((Start)) --> Supervisor
        Supervisor -->|Routing| DataDetective
        Supervisor -->|Routing| Strategist
        Supervisor -->|Routing| Developer
        Supervisor -->|Routing| Reporter
        
        DataDetective --> Supervisor
        Strategist --> Supervisor
        Developer --> Supervisor
        Reporter --> Supervisor
        
        Supervisor -->|Finish| End((End))

        %% Styling (Dark Mode)
        %% Default class (inactive nodes): Dark grey/blue background
        classDef default fill:#161b22,stroke:#30363d,stroke-width:2px,color:#e6edf3;
        
        %% Active class (current node or all finished): Green background
        classDef active fill:#238636,stroke:#3fb950,stroke-width:3px,color:#ffffff;
    `;
    
    // Apply the 'active' class
    if (activeAgent === 'ALL') {
        // Highlight EVERYTHING when finished
        graphDefinition += `\n        class Start,Supervisor,DataDetective,Strategist,Developer,Reporter,End active;`;
    } else if (activeAgent && activeAgent !== '') {
        // Highlight ONLY the current agent
        // Now works because node IDs (e.g., DataDetective) match this name
        graphDefinition += `\n        class ${activeAgent} active;`;
    }
    
    // Clear previous processed attribute to force re-render
    element.removeAttribute('data-processed');
    element.innerHTML = graphDefinition;
    
    if (typeof mermaid !== 'undefined') {
        try {
            await mermaid.run({ nodes: [element] });
        } catch (e) {
            console.error('Mermaid render error:', e);
        }
    }
}