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
const progressSection = document.getElementById('progress-section');
const resultsSection = document.getElementById('results-section');
const downloadsDiv = document.getElementById('downloads');

let uploadedPath = null;

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

async function uploadFile(file, type = 'dataset') {
  const fd = new FormData();
  fd.append('file', file);
  try {
    const r = await fetch(`${API_BASE}/upload`, { method: 'POST', body: fd });
    const data = await r.json();

    if (type === 'dataset') {
      uploadedPath = data.filename;
      fileNameSpan.textContent = `${file.name} (uploaded)`;
    } else {
      // Return the filename for specific field tracking
      return data.filename;
    }
  } catch (e) {
    if (type === 'dataset') {
      fileNameSpan.textContent = `Upload failed: ${e.message}`;
      uploadedPath = null;
    }
    throw e;
  }
}

// Field-specific file inputs
const contextFile = document.getElementById('context-file');
const taskFile = document.getElementById('task-file');
const metadataFile = document.getElementById('metadata-file');

const fieldFiles = {
  context: null,
  task: null,
  metadata: null
};

async function handleFieldFileUpload(input, key, textareaId, nameSpanId) {
  input.addEventListener('change', async () => {
    const file = input.files[0];
    if (!file) return;

    const nameSpan = document.getElementById(nameSpanId);
    nameSpan.textContent = 'Uploading...';
    nameSpan.style.display = 'inline';

    try {
      const serverFilename = await uploadFile(file, 'field');
      fieldFiles[key] = serverFilename;
      nameSpan.textContent = `✓ ${file.name}`;

      // If text/markdown, try to read and populate textarea
      if (file.type === 'text/plain' || file.name.endsWith('.md') || file.name.endsWith('.txt')) {
        const reader = new FileReader();
        reader.onload = (e) => {
          document.getElementById(textareaId).value = e.target.result;
        };
        reader.readAsText(file);
      }
    } catch (e) {
      nameSpan.textContent = 'Failed';
      nameSpan.style.color = 'var(--error)';
    }
  });
}

if (contextFile) handleFieldFileUpload(contextFile, 'context', 'business-context', 'context-file-name');
if (taskFile) handleFieldFileUpload(taskFile, 'task', 'task', 'task-file-name');
if (metadataFile) handleFieldFileUpload(metadataFile, 'metadata', 'metaData', 'metadata-file-name');

function updateGraph(activeAgent) {
  if (!activeAgent) return;
  const agentName = activeAgent.toString();
  // Strip spaces and special chars, e.g. "Data Detective" -> "datadetective"
  const normalizedAgent = agentName.toLowerCase().replace(/[^a-z0-9]/g, '');

  console.log(`[Graph] Update: "${agentName}" -> ID: "node-${normalizedAgent}"`);

  // Update Agent Dashboard (Premium Feedback)
  const thoughtBubble = document.getElementById('agent-thought-bubble');

  if (thoughtBubble) {
    thoughtBubble.classList.remove('hidden');
  }

  // 1. Reset all nodes
  document.querySelectorAll('.node').forEach(node => {
    node.classList.remove('active');
  });

  // 2. Set active node
  const currentNode = document.getElementById(`node-${normalizedAgent}`);
  if (currentNode) {
    currentNode.classList.add('active');
    currentNode.classList.add('completed');
  } else {
    // Fallback search by text content if ID fails (extra safety)
    document.querySelectorAll('.node text').forEach(txt => {
      if (txt.textContent.toLowerCase().includes(normalizedAgent.replace('data', ''))) {
        txt.parentElement.classList.add('active');
        txt.parentElement.classList.add('completed');
      }
    });
  }

  // 3. Highlight edge from Supervisor to active worker
  document.querySelectorAll('.edge').forEach(edge => edge.classList.remove('active'));
  if (normalizedAgent !== 'supervisor' && normalizedAgent !== 'finish') {
    const edgeToWorker = document.getElementById(`path-supervisor-${normalizedAgent}`);
    if (edgeToWorker) {
      edgeToWorker.classList.add('active');
    }
  }
}

function updateThought(agent, message) {
  const thoughtContent = document.getElementById('thought-content');
  if (thoughtContent && agent) {
    if (message.includes('Agent started')) {
      thoughtContent.textContent = `Starting ${agent} phase...`;
    } else if (message.length > 10 && (message.includes('produced') || message.includes('LLM response') || message.includes('Executing'))) {
      // Clean up technical logs for the thought bubble
      const cleanMsg = message.replace(/\[.*?\]/g, '').split('\n')[0].trim();
      thoughtContent.textContent = cleanMsg.length > 100 ? cleanMsg.substring(0, 97) + '...' : cleanMsg;
    }
  }
}

function setStatus(text, className = '') {
  statusValue.textContent = text;
  statusValue.className = 'status-value ' + className;
}

const toggleReport = document.getElementById('toggle-report');
const toggleCode = document.getElementById('toggle-code');
const reportView = document.getElementById('report-view');
const codeView = document.getElementById('code-view');

// Toggle logic
if (toggleReport && toggleCode) {
  toggleReport.addEventListener('click', () => {
    toggleReport.classList.add('active');
    toggleCode.classList.remove('active');
    if (reportView) reportView.classList.remove('hidden');
    if (codeView) codeView.classList.add('hidden');
  });

  toggleCode.addEventListener('click', () => {
    toggleReport.classList.remove('active');
    toggleCode.classList.add('active');
    if (reportView) reportView.classList.add('hidden');
    if (codeView) codeView.classList.remove('hidden');
  });
}

async function showResults(downloads) {
  const reportContainer = document.getElementById('report-container');
  const codeContainer = document.getElementById('code-container');

  resultsSection.classList.remove('hidden');
  resultsSection.classList.add('fadeIn');
  downloadsDiv.innerHTML = '';

  // Reset to report view by default when showing results
  if (toggleReport) toggleReport.click();

  if (reportContainer) reportContainer.innerHTML = 'Loading report...';
  if (codeContainer) codeContainer.textContent = 'Loading code...';

  if (downloads.report) {
    // 1. Render Markdown Report
    try {
      const response = await fetch(`${API_BASE}/download/${downloads.report}`);
      const markdown = await response.text();

      // Configure marked to resolve relative images correctly
      const sessionDir = downloads.report.split('/')[0];
      const renderer = new marked.Renderer();
      const originalImage = renderer.image.bind(renderer);
      renderer.image = (token) => {
        let href = typeof token === 'string' ? token : token.href;
        if (href && !href.startsWith('http') && !href.startsWith('/')) {
          href = `${API_BASE}/download/${sessionDir}/${href}`;
        }
        return originalImage(typeof token === 'string' ? href : { ...token, href });
      };

      reportContainer.innerHTML = marked.parse(markdown, { renderer });

      // Apply Prism highlighting to the newly rendered report content
      if (window.Prism) {
        Prism.highlightAllUnder(reportContainer);
      }
    } catch (e) {
      reportContainer.innerHTML = `<p class="error">Failed to load report: ${e.message}</p>`;
    }

    // 2. Fetch and Highlight Code
    if (downloads.pipeline && codeContainer) {
      try {
        const response = await fetch(`${API_BASE}/download/${downloads.pipeline}`);
        const code = await response.text();
        codeContainer.textContent = code;
        Prism.highlightElement(codeContainer);
      } catch (e) {
        codeContainer.textContent = `Failed to load code: ${e.message}`;
      }
    }

    // 3. Add Download Buttons
    if (downloads.report) {
      const reportBtn = document.createElement('a');
      reportBtn.href = `${API_BASE}/download/${downloads.report}`;
      reportBtn.className = 'btn-download';
      reportBtn.textContent = 'Download Markdown';
      reportBtn.download = 'final_report.md';
      downloadsDiv.appendChild(reportBtn);
    }

    if (downloads.pipeline) {
      const codeBtn = document.createElement('a');
      codeBtn.href = `${API_BASE}/download/${downloads.pipeline}`;
      codeBtn.className = 'btn-download';
      codeBtn.textContent = 'Download Pipeline';
      codeBtn.download = 'pipeline.py';
      downloadsDiv.appendChild(codeBtn);
    }
  }
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();

  const businessContext = document.getElementById('business-context').value.trim();
  const task = document.getElementById('task').value.trim();
  const metaData = document.getElementById('metaData').value.trim()
  const filePaths = uploadedPath ? [uploadedPath] : [];

  runBtn.disabled = true;
  setStatus('Connecting...', 'running');

  // Reset Graph & UI (Premium Reset)
  document.querySelectorAll('.node').forEach(node => {
    node.classList.remove('active');
    node.classList.remove('completed');
  });
  document.querySelectorAll('.edge').forEach(edge => edge.classList.remove('active'));

  const thoughtBubble = document.getElementById('agent-thought-bubble');
  if (thoughtBubble) thoughtBubble.classList.add('hidden');
  const thoughtContent = document.getElementById('thought-content');
  if (thoughtContent) thoughtContent.textContent = 'Initializing mission...';

  const wsUrl = `${(window.location.protocol === 'https:' ? 'wss:' : 'ws:')}//${window.location.host}${API_BASE}/ws/run`;
  const ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    setStatus('Running pipeline...', 'running');
    ws.send(JSON.stringify({
      business_context: businessContext,
      task,
      metaData: metaData,
      file_paths: filePaths,
      context_file: fieldFiles.context,
      task_file: fieldFiles.task,
      metadata_file: fieldFiles.metadata,
    }));
  };

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);

      if (data.type === 'log') {
        const ev = data.event;
        if (ev.agent && ev.message) {
          updateThought(ev.agent, ev.message);
        }
      } else if (data.type === 'progress') {
        updateGraph(data.agent);
        if (data.message && data.message.includes('Agent started')) {
          setStatus(`Current Step: ${data.agent}`, 'running');
        }

        if (data.reason && typeof showReasoning === 'function') {
          showReasoning(data.agent, data.reason);
        }
      } else if (data.type === 'done') {
        setStatus('Done', 'done');
        updateGraph('FINISH');
        showResults(data.downloads || {});
        runBtn.disabled = false;
      } else if (data.type === 'error') {
        setStatus(`Error: ${data.message}`, 'error');
        runBtn.disabled = false;
      }
    } catch (e) {
      console.error(e);
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