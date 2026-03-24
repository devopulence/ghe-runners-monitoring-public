const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');

const MONITORING_DIR = path.join(__dirname, '..', 'monitoring_data');

function loadMonitoringData(org, dateStr) {
  const dateDir = path.join(MONITORING_DIR, org, dateStr);
  const data = { org, date: dateStr, runs: [] };

  const fileKeys = {
    workflow_runs: 'workflow_runs.json',
    jobs: 'jobs.json',
    collection_log: 'collection_log.json',
    computed_metrics: 'computed_metrics.json',
  };

  // Initialize aggregated data
  for (const key of Object.keys(fileKeys)) {
    data[key] = key === 'computed_metrics' ? null : [];
  }

  if (!fs.existsSync(dateDir)) return data;

  // Scan all run directories within the date
  const runDirs = fs.readdirSync(dateDir, { withFileTypes: true })
    .filter(d => d.isDirectory())
    .map(d => d.name)
    .sort();

  data.runs = runDirs;

  for (const runDir of runDirs) {
    const runPath = path.join(dateDir, runDir);
    for (const [key, filename] of Object.entries(fileKeys)) {
      const filePath = path.join(runPath, filename);
      if (fs.existsSync(filePath)) {
        try {
          const parsed = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
          if (key === 'computed_metrics') {
            data[key] = parsed; // use latest
          } else if (Array.isArray(parsed)) {
            data[key] = data[key].concat(parsed);
          }
        } catch (e) {
          console.error(`Error reading ${filePath}:`, e.message);
        }
      }
    }
  }

  return data;
}

function getAvailableOrgs() {
  if (!fs.existsSync(MONITORING_DIR)) return [];

  return fs.readdirSync(MONITORING_DIR, { withFileTypes: true })
    .filter(d => d.isDirectory() && !/^\d{4}-\d{2}-\d{2}$/.test(d.name))
    .map(d => d.name)
    .sort();
}

function getAvailableDates(org) {
  const orgDir = path.join(MONITORING_DIR, org);
  if (!fs.existsSync(orgDir)) return [];

  return fs.readdirSync(orgDir, { withFileTypes: true })
    .filter(d => d.isDirectory() && /^\d{4}-\d{2}-\d{2}$/.test(d.name))
    .map(d => d.name)
    .sort()
    .reverse();
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1500,
    height: 1000,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  win.loadFile('index.html');
}

ipcMain.handle('get-available-orgs', () => {
  return getAvailableOrgs();
});

ipcMain.handle('get-available-dates', (event, org) => {
  return getAvailableDates(org);
});

ipcMain.handle('get-monitoring-data', (event, org, dateStr) => {
  return loadMonitoringData(org, dateStr);
});

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  app.quit();
});