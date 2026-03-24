const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  getAvailableOrgs: () => ipcRenderer.invoke('get-available-orgs'),
  getAvailableDates: (org) => ipcRenderer.invoke('get-available-dates', org),
  getMonitoringData: (org, date) => ipcRenderer.invoke('get-monitoring-data', org, date),
});
