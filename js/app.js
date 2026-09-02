/**
 * AGNIVANI Thermal Intelligence Grid - Application Controller v5.0
 * High-Stakes Industrial & Aerospace Thermal Anomaly Telemetry
 * Enhanced with Web Audio API, Leaflet Interactive Dark Tiles, & FIRMS CSV Ingestion
 */

// --- Global Audio Synthesizer (Web Audio API) ---
const SoundFX = {
  ctx: null,
  enabled: true,

  init() {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        this.ctx = new AudioCtx();
      }
    } catch (e) {
      console.warn('Web Audio API not supported', e);
    }
  },

  resume() {
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  },

  playBlip() {
    if (!this.enabled || !this.ctx) return;
    this.resume();
    try {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(1200, this.ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(1800, this.ctx.currentTime + 0.05);

      gain.gain.setValueAtTime(0.08, this.ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + 0.05);

      osc.connect(gain);
      gain.connect(this.ctx.destination);

      osc.start();
      osc.stop(this.ctx.currentTime + 0.05);
    } catch (e) {}
  },

  playCritical() {
    if (!this.enabled || !this.ctx) return;
    this.resume();
    try {
      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'sawtooth';
      
      osc.frequency.setValueAtTime(440, now);
      osc.frequency.setValueAtTime(880, now + 0.1);
      osc.frequency.setValueAtTime(440, now + 0.2);
      osc.frequency.setValueAtTime(880, now + 0.3);

      gain.gain.setValueAtTime(0.12, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.4);

      osc.connect(gain);
      gain.connect(this.ctx.destination);

      osc.start();
      osc.stop(now + 0.4);
    } catch (e) {}
  },

  playDispatch() {
    if (!this.enabled || !this.ctx) return;
    this.resume();
    try {
      const now = this.ctx.currentTime;
      [440, 554.37, 659.25, 880].forEach((freq, idx) => {
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(freq, now + idx * 0.06);

        gain.gain.setValueAtTime(0.1, now + idx * 0.06);
        gain.gain.exponentialRampToValueAtTime(0.001, now + idx * 0.06 + 0.18);

        osc.connect(gain);
        gain.connect(this.ctx.destination);

        osc.start(now + idx * 0.06);
        osc.stop(now + idx * 0.06 + 0.2);
      });
    } catch (e) {}
  },

  toggle() {
    this.enabled = !this.enabled;
    const btn = document.getElementById('audio-toggle-btn');
    if (btn) {
      btn.innerHTML = `<span class="material-symbols-outlined text-[18px] ${this.enabled ? 'text-primary' : 'text-on-surface-variant'}">${this.enabled ? 'volume_up' : 'volume_off'}</span>`;
      btn.title = `Sound FX: ${this.enabled ? 'ON' : 'OFF'}`;
    }
    if (this.enabled) this.playBlip();
  }
};

// --- Global Application State ---
const AppState = {
  activeView: 'mission-control',
  selectedAnomalyId: 'AGN-04832',
  selectedFacilityId: 'RIL-JAM-01',
  systemTimeOffset: 0,
  terminalPaused: false,
  mapMode: 'vector', // 'vector' | 'satellite'
  leafletMap: null,
  leafletMarkers: [],

  // Live Anomaly Dataset (VIIRS 375m & FIRMS Persistent Sources)
  anomalies: [
    {
      id: 'AGN-04832',
      shortId: 'A94X',
      name: 'Jamnagar Refinery',
      facilityId: 'RIL-JAM-01',
      coords: { lat: 22.35, lon: 70.02 },
      coordsStr: '22.350° N, 70.020° E',
      time: '14:02:11 UTC',
      timestamp: '14:02:11',
      severity: 'CRITICAL',
      type: 'GAS FLARE',
      typeColor: '#ffa94d',
      sevColor: '#ff4d4d',
      confidence: 0.943,
      effTemp: '1847 K',
      tempValue: 1847,
      area: '12.4 m²',
      frp: '62.1 MW',
      frpValue: 62.1,
      swirRad: '14.8 W/m²/sr/μm',
      mwirRad: '8.2 W/m²/sr/μm',
      ch4Est: '0.42 kg/s',
      status: 'DISPATCHED',
      dispatchTime: '14:02Z',
      receivedTime: '14:05Z',
      respondedTime: 'PENDING',
      authority: 'Dist. Collector - SEC 7 (AUTH-7A)'
    },
    {
      id: 'AGN-04831',
      shortId: 'B21Y',
      name: 'Hazira LNG/Steel Complex',
      facilityId: 'HAZ-LNG-02',
      coords: { lat: 21.13, lon: 72.64 },
      coordsStr: '21.130° N, 72.640° E',
      time: '13:58:44 UTC',
      timestamp: '13:58:44',
      severity: 'HIGH',
      type: 'GAS FLARE',
      typeColor: '#ffa94d',
      sevColor: '#ffb13b',
      confidence: 0.912,
      effTemp: '1620 K',
      tempValue: 1620,
      area: '9.8 m²',
      frp: '41.5 MW',
      frpValue: 41.5,
      swirRad: '11.2 W/m²/sr/μm',
      mwirRad: '6.4 W/m²/sr/μm',
      ch4Est: '0.28 kg/s',
      status: 'RECEIVED',
      dispatchTime: '13:59Z',
      receivedTime: '14:01Z',
      respondedTime: '14:10Z',
      authority: 'Hazira Industrial Safety Directorate'
    },
    {
      id: 'AGN-04829',
      shortId: 'C55Z',
      name: 'Vadinar Marine Terminal',
      facilityId: 'VAD-MAR-03',
      coords: { lat: 22.56, lon: 69.73 },
      coordsStr: '22.560° N, 69.730° E',
      time: '13:45:18 UTC',
      timestamp: '13:45:18',
      severity: 'HIGH',
      type: 'INDUSTRIAL FIRE',
      typeColor: '#ff4d4d',
      sevColor: '#ffb13b',
      confidence: 0.885,
      effTemp: '1250 K',
      tempValue: 1250,
      area: '34.2 m²',
      frp: '38.0 MW',
      frpValue: 38.0,
      swirRad: '7.8 W/m²/sr/μm',
      mwirRad: '5.9 W/m²/sr/μm',
      ch4Est: '--',
      status: 'RESPONDED',
      dispatchTime: '13:46Z',
      receivedTime: '13:48Z',
      respondedTime: '14:00Z',
      authority: 'Kandla Coast Guard & Disaster Cell'
    },
    {
      id: 'AGN-04820',
      shortId: 'D18K',
      name: 'Panipat Petrochemical Complex',
      facilityId: 'IOCL-PAN-04',
      coords: { lat: 29.39, lon: 76.97 },
      coordsStr: '29.390° N, 76.970° E',
      time: '13:12:05 UTC',
      timestamp: '13:12:05',
      severity: 'WARNING',
      type: 'COAL SEAM',
      typeColor: '#f59e0b',
      sevColor: '#ffd6a3',
      confidence: 0.792,
      effTemp: '890 K',
      tempValue: 890,
      area: '85.0 m²',
      frp: '18.4 MW',
      frpValue: 18.4,
      swirRad: '3.1 W/m²/sr/μm',
      mwirRad: '3.8 W/m²/sr/μm',
      ch4Est: '--',
      status: 'RESPONDED',
      dispatchTime: '13:14Z',
      receivedTime: '13:18Z',
      respondedTime: '13:35Z',
      authority: 'Haryana State Disaster Management Authority'
    },
    {
      id: 'AGN-04815',
      shortId: 'E09M',
      name: 'Dahej Petrochem SEZ',
      facilityId: 'DHJ-SEZ-05',
      coords: { lat: 21.71, lon: 72.58 },
      coordsStr: '21.710° N, 72.580° E',
      time: '12:49:33 UTC',
      timestamp: '12:49:33',
      severity: 'CRITICAL',
      type: 'GAS LEAK',
      typeColor: '#b197fc',
      sevColor: '#ff4d4d',
      confidence: 0.961,
      effTemp: '1410 K',
      tempValue: 1410,
      area: '18.6 m²',
      frp: '29.7 MW',
      frpValue: 29.7,
      swirRad: '9.4 W/m²/sr/μm',
      mwirRad: '6.1 W/m²/sr/μm',
      ch4Est: '1.15 kg/s',
      status: 'DISPATCHED',
      dispatchTime: '12:50Z',
      receivedTime: '12:52Z',
      respondedTime: 'PENDING',
      authority: 'Gujarat Pollution Control Board Emergency Cell'
    }
  ],

  // Audit Trail Records
  auditTrail: [
    { timestamp: '14:05:22.451', operatorId: 'OP-883A', action: 'Confirm coordinates & radiance verification', ref: 'AGN-04832' },
    { timestamp: '14:02:10.019', operatorId: 'SYS-AUTO', action: 'Alert generated; dispatched to authorities via SAT-RELAY', ref: 'AGN-04832' },
    { timestamp: '13:58:45.102', operatorId: 'SYS-AUTO', action: 'VIIRS Day/Night Band radiance exceeded 4.2-sigma threshold', ref: 'AGN-04831' },
    { timestamp: '13:48:12.770', operatorId: 'OP-702B', action: 'Action checklist completed; nodal team notified', ref: 'AGN-04829' },
    { timestamp: '13:45:00.000', operatorId: 'SYS-AUTO', action: 'Routine VIIRS pass orbital cycle completed (NOAA-20)', ref: 'SYS-00000' }
  ]
};

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
  SoundFX.init();
  initClock();
  initRouting();
  initAlertFeed();
  initMapCanvas();
  initSwipeSlider();
  initTerminalLog();
  initHeatmap();
  initPlanckCurve();
  initAuditTable();
  initEventListeners();
  initCSVUploader();
});

// --- Mission Clock ---
function initClock() {
  const clockEl = document.getElementById('system-clock');
  function update() {
    const now = new Date();
    const timeStr = now.toISOString().substring(11, 19);
    if (clockEl) {
      clockEl.innerText = 'T-' + timeStr;
    }
    const liveTimes = document.querySelectorAll('.live-time-now');
    liveTimes.forEach(el => el.innerText = timeStr + ' UTC');
  }
  update();
  setInterval(update, 1000);
}

// --- Navigation / Routing Engine ---
function initRouting() {
  const hash = window.location.hash.replace('#', '');
  if (['mission-control', 'alerts', 'analytics', 'dossier', 'facility'].includes(hash)) {
    switchView(hash);
  } else {
    switchView('mission-control');
  }

  window.addEventListener('hashchange', () => {
    const newHash = window.location.hash.replace('#', '');
    if (['mission-control', 'alerts', 'analytics', 'dossier', 'facility'].includes(newHash)) {
      switchView(newHash);
    }
  });

  document.querySelectorAll('[data-nav-target]').forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const target = link.getAttribute('data-nav-target');
      SoundFX.playBlip();
      switchView(target);
      window.location.hash = target;
    });
  });
}

function switchView(viewName) {
  AppState.activeView = viewName;
  
  document.querySelectorAll('.view-panel').forEach(panel => {
    panel.classList.remove('active');
  });

  const targetPanel = document.getElementById(`view-${viewName}`);
  if (targetPanel) {
    targetPanel.classList.add('active');
  }

  document.querySelectorAll('[data-nav-target]').forEach(link => {
    const target = link.getAttribute('data-nav-target');
    if (target === viewName) {
      link.classList.add('bg-secondary-container', 'text-primary', 'border-r-2', 'border-primary', 'brightness-125');
      link.classList.remove('text-on-surface-variant');
    } else {
      link.classList.remove('bg-secondary-container', 'text-primary', 'border-r-2', 'border-primary', 'brightness-125');
      link.classList.add('text-on-surface-variant');
    }
  });

  if (viewName === 'dossier') {
    setTimeout(initSwipeSlider, 60);
  }
  if (viewName === 'mission-control' && AppState.mapMode === 'satellite') {
    setTimeout(refreshLeafletMap, 60);
  }
}

// --- Live Alert Feed & Inspector Engine ---
function initAlertFeed() {
  const alertFeedContainer = document.getElementById('alert-feed');
  const alertQueueContainer = document.getElementById('queue-alert-list');

  if (alertFeedContainer) {
    alertFeedContainer.innerHTML = '';
    AppState.anomalies.forEach(anomaly => {
      const isSelected = anomaly.id === AppState.selectedAnomalyId;
      const card = document.createElement('div');
      card.className = `hud-border p-xs rounded-sm cursor-pointer relative overflow-hidden transition-all ${
        isSelected ? 'bg-surface-container border-primary/50' : 'bg-[#0d141d]/50 hover:bg-surface-container'
      }`;
      card.innerHTML = `
        ${isSelected ? '<div class="absolute left-0 top-0 bottom-0 w-1 bg-primary"></div>' : ''}
        <div class="flex justify-between items-start mb-xs ${isSelected ? 'pl-1' : ''}">
          <div class="flex items-center gap-xs">
            <div class="px-1 rounded-sm flex items-center h-4 border" style="background-color: ${anomaly.sevColor}22; border-color: ${anomaly.sevColor}">
              <span class="font-label-caps text-[8px]" style="color: ${anomaly.sevColor}">${anomaly.severity}</span>
            </div>
            <span class="font-data-mono text-[10px] ${isSelected ? 'text-primary font-bold' : 'text-on-surface-variant'}">ID:${anomaly.shortId}</span>
          </div>
          <span class="font-data-mono text-[10px] text-on-surface-variant">${anomaly.timestamp}</span>
        </div>
        <div class="${isSelected ? 'pl-1' : ''}">
          <div class="font-body-md text-[12px] font-semibold text-on-surface truncate">${anomaly.name}</div>
          <div class="flex gap-sm mt-[2px]">
            <span class="font-data-mono text-[10px] text-on-surface-variant">${anomaly.effTemp}</span>
            <span class="font-data-mono text-[10px] text-on-surface-variant">${anomaly.frp}</span>
          </div>
        </div>
      `;

      card.addEventListener('click', () => {
        SoundFX.playBlip();
        selectAnomaly(anomaly.id);
      });

      alertFeedContainer.appendChild(card);
    });
  }

  if (alertQueueContainer) {
    alertQueueContainer.innerHTML = '';
    AppState.anomalies.forEach(anomaly => {
      const isSelected = anomaly.id === AppState.selectedAnomalyId;
      const item = document.createElement('div');
      item.className = `p-sm border-b border-[#1b2735] relative group cursor-pointer transition-colors ${
        isSelected ? 'bg-secondary-container/30' : 'hover:bg-surface-container-highest'
      }`;
      item.innerHTML = `
        <div class="absolute left-0 top-0 bottom-0 w-[2px]" style="background-color: ${anomaly.sevColor}"></div>
        <div class="flex justify-between items-start mb-xs pl-xs">
          <div class="flex items-center gap-xs">
            <input type="checkbox" ${isSelected ? 'checked' : ''} class="w-3 h-3 bg-transparent border-outline-variant rounded-[2px] text-primary focus:ring-0">
            <span class="text-data-mono font-data-mono text-[11px] ${isSelected ? 'text-primary font-bold' : 'text-on-surface'}">${anomaly.id}</span>
          </div>
          <span class="text-data-mono font-data-mono text-[10px]" style="color: ${anomaly.sevColor}">${anomaly.timestamp}</span>
        </div>
        <div class="pl-xs flex gap-xs items-center mt-xs">
          <div class="px-xs py-[2px] rounded-[2px] text-[9px] font-label-caps flex items-center gap-[2px] border" style="background-color: ${anomaly.sevColor}22; border-color: ${anomaly.sevColor}; color: ${anomaly.sevColor}">
            <div class="w-1.5 h-1.5 rounded-sm ${anomaly.severity === 'CRITICAL' ? 'animate-pulse' : ''}" style="background-color: ${anomaly.sevColor}"></div>
            ${anomaly.severity}
          </div>
          <span class="text-on-surface-variant text-[10px] font-data-mono truncate">${anomaly.name}</span>
        </div>
      `;

      item.addEventListener('click', () => {
        SoundFX.playBlip();
        selectAnomaly(anomaly.id);
      });

      alertQueueContainer.appendChild(item);
    });
  }
}

function selectAnomaly(id) {
  AppState.selectedAnomalyId = id;
  const item = AppState.anomalies.find(a => a.id === id);
  if (!item) return;

  if (item.severity === 'CRITICAL') {
    SoundFX.playCritical();
  }

  // Refresh feeds
  initAlertFeed();

  // If in satellite mode, fly to marker
  if (AppState.mapMode === 'satellite' && AppState.leafletMap) {
    AppState.leafletMap.flyTo([item.coords.lat, item.coords.lon], 7, { duration: 1.2 });
  }

  // Update Inspector in Mission Control
  const inspSelectedId = document.getElementById('insp-selected-id');
  const inspName = document.getElementById('insp-name');
  const inspType = document.getElementById('insp-type');
  const inspConf = document.getElementById('insp-conf');
  const inspTemp = document.getElementById('insp-temp');
  const inspArea = document.getElementById('insp-area');
  const inspFrp = document.getElementById('insp-frp');
  const inspCh4 = document.getElementById('insp-ch4');

  if (inspSelectedId) inspSelectedId.innerText = `ID: ${item.shortId}`;
  if (inspName) inspName.innerText = item.name;
  if (inspType) {
    inspType.innerText = item.type;
    inspType.style.color = item.typeColor;
  }
  if (inspConf) inspConf.innerText = `p=${item.confidence.toFixed(3)}`;
  if (inspTemp) inspTemp.innerText = item.effTemp;
  if (inspArea) inspArea.innerText = item.area;
  if (inspFrp) inspFrp.innerText = item.frp;
  if (inspCh4) inspCh4.innerText = item.ch4Est;

  // Update Incident Summary in Alert Console
  const alertSumId = document.getElementById('summary-anomaly-id');
  const alertSumSev = document.getElementById('summary-severity-badge');
  const alertSumCoords = document.getElementById('summary-coords');
  if (alertSumId) alertSumId.innerText = item.id;
  if (alertSumSev) {
    alertSumSev.innerHTML = `<span class="material-symbols-outlined text-[16px]">warning</span> ${item.severity}`;
    alertSumSev.style.color = item.sevColor;
  }
  if (alertSumCoords) alertSumCoords.innerText = `${item.name}: ${item.coordsStr}`;

  // Update Dossier Info
  const dossierId = document.getElementById('dossier-id');
  const dossierType = document.getElementById('dossier-type');
  const dossierSev = document.getElementById('dossier-severity');
  const dossierFacility = document.getElementById('dossier-facility');
  if (dossierId) dossierId.innerText = `ID ${item.id}`;
  if (dossierType) {
    dossierType.innerText = item.type;
    dossierType.style.color = item.typeColor;
    dossierType.style.borderColor = item.typeColor;
    dossierType.style.backgroundColor = `${item.typeColor}22`;
  }
  if (dossierSev) {
    dossierSev.innerHTML = `<span class="material-symbols-outlined text-[12px]">warning</span> ${item.severity}`;
    dossierSev.style.color = item.sevColor;
  }
  if (dossierFacility) dossierFacility.innerText = item.name.toUpperCase();

  appendTerminalLog(`[PHYS] Retargeted spectrometer to ${item.id} (${item.name}). T_eff=${item.effTemp}, FRP=${item.frp}`);
}

// --- Interactive Map HUD Engine (Vector & Leaflet Satellite Mode) ---
function initMapCanvas() {
  const mapContainer = document.getElementById('mission-map-svg');
  if (!mapContainer) return;

  mapContainer.innerHTML = '';

  // Draw custom high-tech dark vector map background & beacons
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 1000 600');
  svg.setAttribute('class', 'w-full h-full');

  // India Contour simplified path
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('d', 'M 280,120 L 320,110 L 350,140 L 370,180 L 380,240 L 420,270 L 460,260 L 520,290 L 530,340 L 490,380 L 450,420 L 400,490 L 360,540 L 340,510 L 310,440 L 290,380 L 260,330 L 240,260 L 250,180 Z');
  path.setAttribute('fill', 'rgba(13, 20, 29, 0.4)');
  path.setAttribute('stroke', '#1b2735');
  path.setAttribute('stroke-width', '1.5');
  svg.appendChild(path);

  // Add Coordinate Grids
  for (let x = 100; x < 900; x += 150) {
    const gridLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    gridLine.setAttribute('x1', x);
    gridLine.setAttribute('y1', '0');
    gridLine.setAttribute('x2', x);
    gridLine.setAttribute('y2', '600');
    gridLine.setAttribute('stroke', '#1b2735');
    gridLine.setAttribute('stroke-dasharray', '4,4');
    gridLine.setAttribute('opacity', '0.4');
    svg.appendChild(gridLine);
  }

  // Plot Hotspots from AppState.anomalies
  AppState.anomalies.forEach((anomaly) => {
    const x = 240 + (anomaly.coords.lon - 68) * 28;
    const y = 520 - (anomaly.coords.lat - 18) * 26;

    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.setAttribute('class', 'cursor-pointer group');
    g.setAttribute('transform', `translate(${x}, ${y})`);

    const circleRing = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circleRing.setAttribute('r', '16');
    circleRing.setAttribute('fill', 'none');
    circleRing.setAttribute('stroke', anomaly.typeColor);
    circleRing.setAttribute('stroke-width', '0.75');
    circleRing.setAttribute('stroke-dasharray', '3,3');
    circleRing.setAttribute('opacity', '0.6');
    g.appendChild(circleRing);

    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('r', '6');
    circle.setAttribute('fill', anomaly.typeColor);
    circle.setAttribute('class', anomaly.severity === 'CRITICAL' ? 'pulse-critical' : '');
    g.appendChild(circle);

    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('x', '18');
    text.setAttribute('y', '4');
    text.setAttribute('fill', '#e0e2ed');
    text.setAttribute('font-family', 'JetBrains Mono');
    text.setAttribute('font-size', '10px');
    text.setAttribute('font-weight', 'bold');
    text.textContent = `${anomaly.shortId} | ${anomaly.name}`;
    g.appendChild(text);

    g.addEventListener('click', () => {
      SoundFX.playBlip();
      selectAnomaly(anomaly.id);
    });

    svg.appendChild(g);
  });

  mapContainer.appendChild(svg);
}

// --- Real Leaflet Dark Matter Satellite Engine ---
function setMapMode(mode) {
  AppState.mapMode = mode;
  const vectorContainer = document.getElementById('mission-map-svg');
  const leafletContainer = document.getElementById('leaflet-map-container');
  const radarSweep = document.getElementById('map-radar-sweep');
  const btnVector = document.getElementById('btn-map-vector');
  const btnSat = document.getElementById('btn-map-satellite');

  SoundFX.playBlip();

  if (mode === 'satellite') {
    if (vectorContainer) vectorContainer.classList.add('hidden');
    if (radarSweep) radarSweep.classList.add('hidden');
    if (leafletContainer) leafletContainer.classList.remove('hidden');

    if (btnVector) btnVector.classList.remove('bg-primary-container', 'text-[#060910]', 'font-bold');
    if (btnVector) btnVector.classList.add('bg-surface-container', 'text-on-surface-variant');
    if (btnSat) btnSat.classList.add('bg-primary-container', 'text-[#060910]', 'font-bold');
    if (btnSat) btnSat.classList.remove('bg-surface-container', 'text-on-surface-variant');

    initLeafletMap();
    appendTerminalLog('[MAP] Switched to CartoDB Dark Matter Satellite telemetry layer');
  } else {
    if (vectorContainer) vectorContainer.classList.remove('hidden');
    if (radarSweep) radarSweep.classList.remove('hidden');
    if (leafletContainer) leafletContainer.classList.add('hidden');

    if (btnVector) btnVector.classList.add('bg-primary-container', 'text-[#060910]', 'font-bold');
    if (btnVector) btnVector.classList.remove('bg-surface-container', 'text-on-surface-variant');
    if (btnSat) btnSat.classList.remove('bg-primary-container', 'text-[#060910]', 'font-bold');
    if (btnSat) btnSat.classList.add('bg-surface-container', 'text-on-surface-variant');

    appendTerminalLog('[MAP] Switched to Vector HUD Telemetry mode');
  }
}

function initLeafletMap() {
  if (typeof L === 'undefined') return;
  const container = document.getElementById('leaflet-map-container');
  if (!container) return;

  if (!AppState.leafletMap) {
    AppState.leafletMap = L.map('leaflet-map-container', {
      center: [22.8, 72.5],
      zoom: 6,
      zoomControl: false,
      attributionControl: false
    });

    L.control.zoom({ position: 'topright' }).addTo(AppState.leafletMap);

    // Dark Matter CartoDB Basemap
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
      subdomains: 'abcd'
    }).addTo(AppState.leafletMap);
  }

  refreshLeafletMap();
}

function refreshLeafletMap() {
  if (!AppState.leafletMap || typeof L === 'undefined') return;

  AppState.leafletMap.invalidateSize();

  // Clear existing markers
  AppState.leafletMarkers.forEach(m => AppState.leafletMap.removeLayer(m));
  AppState.leafletMarkers = [];

  // Plot current anomalies
  AppState.anomalies.forEach(anomaly => {
    const customIcon = L.divIcon({
      className: 'custom-div-icon',
      html: `<div style="width: 20px; height: 20px; background-color: ${anomaly.typeColor}; border: 2px solid #ffffff; border-radius: 50%; box-shadow: 0 0 10px ${anomaly.typeColor};" class="${anomaly.severity === 'CRITICAL' ? 'pulse-critical' : ''}"></div>`,
      iconSize: [20, 20],
      iconAnchor: [10, 10]
    });

    const marker = L.marker([anomaly.coords.lat, anomaly.coords.lon], { icon: customIcon }).addTo(AppState.leafletMap);

    marker.bindPopup(`
      <div style="font-family: 'JetBrains Mono', monospace; font-size: 11px;">
        <strong style="color: ${anomaly.typeColor}">${anomaly.name}</strong><br/>
        ID: <span style="color: #22d3ee">${anomaly.id}</span><br/>
        Type: ${anomaly.type}<br/>
        Temp: <span style="color: #ff4d4d">${anomaly.effTemp}</span> | FRP: ${anomaly.frp}<br/>
        <button onclick="selectAnomaly('${anomaly.id}')" style="margin-top: 6px; padding: 2px 8px; background: #22d3ee; color: #060910; border: none; border-radius: 2px; font-weight: bold; cursor: pointer;">INSPECT</button>
      </div>
    `);

    marker.on('click', () => {
      SoundFX.playBlip();
      selectAnomaly(anomaly.id);
    });

    AppState.leafletMarkers.push(marker);
  });
}

// --- Visual Proof Before/After Swipe Slider Engine ---
function initSwipeSlider() {
  const container = document.getElementById('swipe-container');
  const handle = document.getElementById('swipe-handle');
  const afterImg = document.getElementById('swipe-after');

  if (!container || !handle || !afterImg) return;

  let isDragging = false;

  function updateSlider(clientX) {
    const rect = container.getBoundingClientRect();
    let pos = (clientX - rect.left) / rect.width;
    pos = Math.max(0.05, Math.min(0.95, pos));
    const percentage = pos * 100;

    handle.style.left = `${percentage}%`;
    afterImg.style.clipPath = `polygon(${percentage}% 0, 100% 0, 100% 100%, ${percentage}% 100%)`;
  }

  handle.addEventListener('mousedown', (e) => {
    isDragging = true;
    e.preventDefault();
  });

  window.addEventListener('mouseup', () => {
    isDragging = false;
  });

  window.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    updateSlider(e.clientX);
  });

  handle.addEventListener('touchstart', () => {
    isDragging = true;
  });

  window.addEventListener('touchend', () => {
    isDragging = false;
  });

  window.addEventListener('touchmove', (e) => {
    if (!isDragging || !e.touches[0]) return;
    updateSlider(e.touches[0].clientX);
  });
}

// --- Live Terminal Stream Simulator ---
function initTerminalLog() {
  const logContainer = document.getElementById('terminal-log');
  if (!logContainer) return;

  const mockLogs = [
    { mod: '[GEE]', color: 'text-primary-container', msg: 'VIIRS granules ingest stream active (NOAA-20 orbit #34891)' },
    { mod: '[PHYS]', color: 'text-tertiary-container', msg: 'Spectral radiance solver computed dual-band temp: 1847.2 K' },
    { mod: '[BASE]', color: 'text-[#ffa94d]', msg: 'Background contextualization: Anomaly delta > 4.6 sigma relative to 30d baseline' },
    { mod: '[FUSE]', color: 'text-error', msg: 'Multi-band saturation confirmed on I4 band at coords 22.35N, 70.02E' },
    { mod: '[CLASS]', color: 'text-primary', msg: 'XGBoost v4.2 inference verdict: GAS FLARE (confidence p=0.943)' },
    { mod: '[NPS]', color: 'text-secondary', msg: 'Persistent Source Register matched: RIL-JAM-01 (100% historical persistence)' }
  ];

  let logIndex = 0;
  setInterval(() => {
    if (AppState.terminalPaused) return;
    const item = mockLogs[logIndex % mockLogs.length];
    const now = new Date();
    const ts = now.toISOString().substring(11, 19);
    appendTerminalLog(`<span class="text-on-surface-variant/50">[${ts}]</span> <span class="${item.color}">${item.mod}</span> ${item.msg}`);
    logIndex++;
  }, 4000);
}

function appendTerminalLog(htmlMsg) {
  const logContainer = document.getElementById('terminal-log');
  if (!logContainer) return;
  const div = document.createElement('div');
  div.innerHTML = htmlMsg;
  logContainer.appendChild(div);
  logContainer.scrollTop = logContainer.scrollHeight;
}

// --- 365-Day Activity Heatmap Grid ---
function initHeatmap() {
  const container = document.getElementById('facility-heatmap-grid');
  if (!container) return;

  container.innerHTML = '';
  const colors = [
    'bg-surface-container-highest',
    'bg-surface-container-highest',
    'bg-primary/30',
    'bg-primary/60',
    'bg-primary',
    'bg-[#ffa94d]',
    'bg-error'
  ];

  const startDate = new Date();
  startDate.setDate(startDate.getDate() - 364);

  for (let i = 0; i < 364; i++) {
    const curDate = new Date(startDate);
    curDate.setDate(curDate.getDate() + i);
    const dateStr = curDate.toISOString().substring(0, 10);
    
    let colorIdx = 0;
    const r = Math.random();
    if (r > 0.85) colorIdx = 6;
    else if (r > 0.70) colorIdx = 5;
    else if (r > 0.50) colorIdx = 4;
    else if (r > 0.35) colorIdx = 3;
    else if (r > 0.20) colorIdx = 2;
    else colorIdx = 0;

    const count = colorIdx === 0 ? 0 : Math.floor(colorIdx * 2.5 + Math.random() * 3);

    const cell = document.createElement('div');
    cell.className = `w-full h-[9px] rounded-sm transition-all hover:scale-125 hover:z-20 cursor-pointer ${colors[colorIdx]}`;
    cell.setAttribute('title', `${dateStr}: ${count} thermal detections (${count > 0 ? (count * 14.2).toFixed(1) + ' MW' : 'Nominal'})`);
    container.appendChild(cell);
  }
}

// --- Planck Radiation Curve Renderer ---
function initPlanckCurve() {
  const curveSvg = document.getElementById('planck-svg-curve');
  if (!curveSvg) return;

  const T = 1847;
  let pathD = 'M 0 180';
  for (let x = 0; x <= 500; x += 10) {
    const lambda = 0.5 + (x / 500) * 4.5;
    const peak = 2898 / T;
    const diff = Math.abs(lambda - peak);
    const intensity = Math.exp(-Math.pow(diff / 0.8, 2));
    const y = 180 - intensity * 150;
    pathD += ` L ${x} ${y.toFixed(1)}`;
  }

  curveSvg.setAttribute('d', pathD);
}

// --- Immutable Audit Table Engine ---
function initAuditTable() {
  const tbody = document.getElementById('audit-table-body');
  if (!tbody) return;

  tbody.innerHTML = '';
  AppState.auditTrail.forEach((record, index) => {
    const tr = document.createElement('tr');
    tr.className = `border-b border-[#1b2735] ${index % 2 === 1 ? 'bg-white/[0.02]' : ''} hover:bg-[#1b2735]/50 transition-colors`;
    tr.innerHTML = `
      <td class="p-xs text-on-surface-variant font-data-mono text-[11px]">${record.timestamp}</td>
      <td class="p-xs text-primary font-data-mono text-[11px]">${record.operatorId}</td>
      <td class="p-xs font-data-mono text-[11px]">${record.action}</td>
      <td class="p-xs text-on-surface-variant font-data-mono text-[11px]">${record.ref}</td>
    `;
    tbody.appendChild(tr);
  });
}

// --- CSV Drag-and-Drop & File Ingestion Engine ---
function initCSVUploader() {
  const modal = document.getElementById('csv-modal');
  const openBtn = document.getElementById('open-csv-btn');
  const closeBtn = document.getElementById('close-csv-btn');
  const dropzone = document.getElementById('csv-dropzone');
  const fileInput = document.getElementById('csv-file-input');
  const sampleBtn = document.getElementById('load-sample-csv-btn');

  if (openBtn && modal) {
    openBtn.addEventListener('click', () => {
      SoundFX.playBlip();
      modal.classList.remove('hidden');
    });
  }

  if (closeBtn && modal) {
    closeBtn.addEventListener('click', () => {
      modal.classList.add('hidden');
    });
  }

  if (dropzone && fileInput) {
    dropzone.addEventListener('click', () => fileInput.click());

    dropzone.addEventListener('dragover', (e) => {
      e.preventDefault();
      dropzone.classList.add('drag-over');
    });

    dropzone.addEventListener('dragleave', () => {
      dropzone.classList.remove('drag-over');
    });

    dropzone.addEventListener('drop', (e) => {
      e.preventDefault();
      dropzone.classList.remove('drag-over');
      if (e.dataTransfer.files.length > 0) {
        handleCSVFile(e.dataTransfer.files[0]);
      }
    });

    fileInput.addEventListener('change', (e) => {
      if (e.target.files.length > 0) {
        handleCSVFile(e.target.files[0]);
      }
    });
  }

  if (sampleBtn) {
    sampleBtn.addEventListener('click', () => {
      loadSampleFirmsCSV();
    });
  }
}

function handleCSVFile(file) {
  const reader = new FileReader();
  reader.onload = function(e) {
    const text = e.target.result;
    parseAndIngestCSV(text, file.name);
  };
  reader.readAsText(file);
}

function parseAndIngestCSV(csvText, filename = 'custom_firms.csv') {
  const lines = csvText.trim().split(/\r?\n/);
  if (lines.length < 2) {
    alert('Invalid CSV file: missing rows.');
    return;
  }

  const headers = lines[0].split(',').map(h => h.trim().toLowerCase());
  const latIdx = headers.indexOf('latitude');
  const lonIdx = headers.indexOf('longitude');
  const frpIdx = headers.indexOf('frp');
  const ti4Idx = headers.indexOf('bright_ti4');
  const facilityIdx = headers.indexOf('nearest_facility');

  if (latIdx === -1 || lonIdx === -1) {
    alert('CSV missing required "latitude" and "longitude" columns.');
    return;
  }

  const parsedAnomalies = [];
  for (let i = 1; i < lines.length; i++) {
    const cols = lines[i].split(',').map(c => c.trim());
    if (cols.length <= latIdx || cols.length <= lonIdx) continue;

    const lat = parseFloat(cols[latIdx]);
    const lon = parseFloat(cols[lonIdx]);
    if (isNaN(lat) || isNaN(lon)) continue;

    const frp = frpIdx !== -1 ? parseFloat(cols[frpIdx]) || 15.0 : 25.0;
    const ti4 = ti4Idx !== -1 ? parseFloat(cols[ti4Idx]) || 340.0 : 350.0;
    const facility = facilityIdx !== -1 && cols[facilityIdx] ? cols[facilityIdx] : `Cell (${lat.toFixed(2)}, ${lon.toFixed(2)})`;

    // Heuristic Classification
    let type = 'GAS FLARE';
    let typeColor = '#ffa94d';
    let severity = 'HIGH';
    let sevColor = '#ffb13b';

    if (ti4 > 360 || frp > 50) {
      severity = 'CRITICAL';
      sevColor = '#ff4d4d';
    } else if (frp < 10) {
      severity = 'WARNING';
      sevColor = '#ffd6a3';
    }

    if (facility.toLowerCase().includes('refinery') || facility.toLowerCase().includes('lng') || facility.toLowerCase().includes('port')) {
      type = 'GAS FLARE';
      typeColor = '#ffa94d';
    } else if (facility.toLowerCase().includes('coal') || facility.toLowerCase().includes('thermal')) {
      type = 'COAL SEAM';
      typeColor = '#f59e0b';
    } else {
      type = 'INDUSTRIAL FIRE';
      typeColor = '#ff4d4d';
    }

    parsedAnomalies.push({
      id: `AGN-${10000 + i}`,
      shortId: `F${i.toString(16).toUpperCase()}`,
      name: facility,
      facilityId: `FAC-${100 + i}`,
      coords: { lat, lon },
      coordsStr: `${lat.toFixed(3)}° N, ${lon.toFixed(3)}° E`,
      time: 'LIVE ORBITAL PASS',
      timestamp: 'LIVE',
      severity,
      type,
      typeColor,
      sevColor,
      confidence: 0.85 + Math.random() * 0.12,
      effTemp: `${Math.round(ti4 * 4.2)} K`,
      tempValue: Math.round(ti4 * 4.2),
      area: `${(frp * 0.35).toFixed(1)} m²`,
      frp: `${frp.toFixed(1)} MW`,
      frpValue: frp,
      swirRad: `${(frp * 0.24).toFixed(1)} W/m²/sr/μm`,
      mwirRad: `${(frp * 0.15).toFixed(1)} W/m²/sr/μm`,
      ch4Est: `${(frp * 0.008).toFixed(2)} kg/s`,
      status: 'DISPATCHED',
      dispatchTime: 'NOW',
      receivedTime: 'PENDING',
      respondedTime: 'PENDING',
      authority: 'District Emergency Command Cell'
    });

    if (parsedAnomalies.length >= 25) break; // Keep UI dense and clean
  }

  if (parsedAnomalies.length > 0) {
    AppState.anomalies = parsedAnomalies;
    AppState.selectedAnomalyId = parsedAnomalies[0].id;
    
    // Update UI components
    initAlertFeed();
    initMapCanvas();
    if (AppState.mapMode === 'satellite') {
      refreshLeafletMap();
    }
    selectAnomaly(parsedAnomalies[0].id);

    // Audio & Terminal feedback
    SoundFX.playDispatch();
    appendTerminalLog(`<span class="text-primary font-bold">[INGEST]</span> Ingested ${parsedAnomalies.length} real FIRMS detections from ${filename}`);
    
    const modal = document.getElementById('csv-modal');
    if (modal) modal.classList.add('hidden');
    alert(`Successfully loaded ${parsedAnomalies.length} FIRMS detections from ${filename}!`);
  }
}

function loadSampleFirmsCSV() {
  fetch('firms_india_persistent.csv')
    .then(res => res.text())
    .then(text => {
      parseAndIngestCSV(text, 'firms_india_persistent.csv');
    })
    .catch(() => {
      // Fallback inline sample
      const sample = `latitude,longitude,hits,days,night_hits,median_ti4,median_ti5,max_frp,mean_frp,nearest_facility
21.1,72.64,12,3,7,332.62,292.92,9.54,5.02,Hazira LNG/Steel
22.35,70.02,18,4,9,368.12,305.4,62.1,45.2,Jamnagar Refinery
26.88,73.52,4,3,4,306.56,293.0,2.78,1.66,Bathinda Refinery
23.26,70.26,2,2,2,301.96,285.99,1.26,0.91,Kandla Port
15.18,76.66,6,2,5,321.95,286.77,7.11,3.63,Mangalore Refinery
29.46,76.88,5,2,5,307.39,284.39,5.21,2.91,Panipat Refinery`;
      parseAndIngestCSV(sample, 'firms_india_persistent.csv');
    });
}

// --- Interactive Modal & Event Listeners ---
function initEventListeners() {
  // Audio toggle listener
  const audioBtn = document.getElementById('audio-toggle-btn');
  if (audioBtn) {
    audioBtn.addEventListener('click', () => {
      SoundFX.toggle();
    });
  }

  // Map Switcher buttons
  const btnVector = document.getElementById('btn-map-vector');
  const btnSat = document.getElementById('btn-map-satellite');
  if (btnVector) {
    btnVector.addEventListener('click', () => setMapMode('vector'));
  }
  if (btnSat) {
    btnSat.addEventListener('click', () => setMapMode('satellite'));
  }

  // Dispatch Modal Open
  const dispatchButtons = document.querySelectorAll('[data-action="open-dispatch"]');
  const modal = document.getElementById('dispatch-modal');
  const closeModalBtn = document.getElementById('close-dispatch-modal');
  const confirmDispatchBtn = document.getElementById('confirm-dispatch-btn');

  dispatchButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      SoundFX.playBlip();
      if (modal) modal.classList.remove('hidden');
    });
  });

  if (closeModalBtn && modal) {
    closeModalBtn.addEventListener('click', () => {
      modal.classList.add('hidden');
    });
  }

  if (confirmDispatchBtn && modal) {
    confirmDispatchBtn.addEventListener('click', () => {
      const activeAnomaly = AppState.anomalies.find(a => a.id === AppState.selectedAnomalyId) || AppState.anomalies[0];
      const now = new Date();
      const timeStr = now.toISOString().substring(11, 23);

      AppState.auditTrail.unshift({
        timestamp: timeStr,
        operatorId: 'OP-883A',
        action: `MANUAL DISPATCH CONFIRMED -> Broadcasted priority alert to ${activeAnomaly.authority}`,
        ref: activeAnomaly.id
      });
      initAuditTable();

      SoundFX.playDispatch();
      appendTerminalLog(`[DISPATCH] Priority alert ${activeAnomaly.id} broadcasted to ${activeAnomaly.authority}`);
      modal.classList.add('hidden');
      alert(`Priority alert for ${activeAnomaly.name} (${activeAnomaly.id}) successfully dispatched to Nodal Authorities.`);
    });
  }

  // Action Protocol Checkbox toggles
  document.querySelectorAll('.protocol-checkbox').forEach(cb => {
    cb.addEventListener('change', (e) => {
      SoundFX.playBlip();
      const label = e.target.closest('label')?.querySelector('.protocol-text');
      if (label) {
        if (e.target.checked) {
          label.classList.add('line-through', 'opacity-50');
        } else {
          label.classList.remove('line-through', 'opacity-50');
        }
      }
    });
  });
}
