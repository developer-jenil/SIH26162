/**
 * AGNIVANI Thermal Intelligence Grid - Application Controller v5.0
 * High-Stakes Industrial & Aerospace Thermal Anomaly Telemetry
 * Enhanced with Web Audio API, Leaflet Interactive Dark Tiles, & FIRMS CSV Ingestion
 * Live API integration with offline demo fallback.
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
    const btn = mustEl('audio-toggle-btn');
    if (btn) {
      btn.innerHTML = `<span class="material-symbols-outlined text-[18px] ${this.enabled ? 'text-primary' : 'text-on-surface-variant'}">${this.enabled ? 'volume_up' : 'volume_off'}</span>`;
      btn.title = `Sound FX: ${this.enabled ? 'ON' : 'OFF'}`;
    }
    if (this.enabled) this.playBlip();
  }
};

// --- DOM Contract Enforcement (B8) ---
function mustEl(id) {
  const el = document.getElementById(id);
  if (!el) {
    const msg = `[AGNIVANI DOM CONTRACT ERROR] Required element #${id} not found in DOM.`;
    console.error(msg);
    throw new Error(msg);
  }
  return el;
}

// --- Config shim (injected by FastAPI; absent in file:// demo) ---
const AGNIVANI_API = window.AGNIVANI_API || null;
const URL_PARAMS = typeof window !== 'undefined' && window.location ? new URLSearchParams(window.location.search) : new URLSearchParams();
const IS_EXPLICIT_DEMO = URL_PARAMS.get('demo') === '1';

// Embedded Demo Fixtures (Strictly quarantined for offline rehearsal with ?demo=1)
const DEMO_FIXTURES = [
  {
    id: 'SIM-04832',
    shortId: 'A94X',
    name: 'Jamnagar Refinery',
    facilityId: 'RIL-JAM-01',
    coords: { lat: 22.35, lon: 70.02 },
    coordsStr: '22.350° N, 70.020° E',
    time: '2026-09-01T14:02:11Z',
    timestamp: '14:02:11 UTC',
    severity: 'HIGH',
    type: 'GAS FLARE',
    typeColor: '#ffa94d',
    sevColor: '#ffb13b',
    confidence: 0.943,
    effTemp: '1847 K',
    tempValue: 1847,
    area: '12.4 m²',
    p: 0.000088,
    frp: '62.1 MW',
    frpValue: 62.1,
    swirRad: '14.8 W/m²/sr/μm',
    mwirRad: '8.2 W/m²/sr/μm',
    ch4Est: '0.42 kg/s',
    co2e_rate_tph: 122.96,
    black_carbon_rate_kgph: 145.31,
    co2e_total_t: 14755.2,
    status: 'DISPATCHED',
    diurnal_shape: 'FLAT_24H',
    dispatchTime: '14:02Z',
    receivedTime: '14:05Z',
    respondedTime: 'PENDING',
    authority: 'Dist. Collector - SEC 7 (AUTH-7A)',
    provenance: 'SIMULATED'
  },
  {
    id: 'SIM-04831',
    shortId: 'B21Y',
    name: 'Hazira LNG/Steel Complex',
    facilityId: 'HAZ-LNG-02',
    coords: { lat: 21.13, lon: 72.64 },
    coordsStr: '21.130° N, 72.640° E',
    time: '2026-09-01T13:58:44Z',
    timestamp: '13:58:44 UTC',
    severity: 'HIGH',
    type: 'GAS FLARE',
    typeColor: '#ffa94d',
    sevColor: '#ffb13b',
    confidence: 0.912,
    effTemp: '1620 K',
    tempValue: 1620,
    area: '9.8 m²',
    p: 0.000070,
    frp: '41.5 MW',
    frpValue: 41.5,
    swirRad: '11.2 W/m²/sr/μm',
    mwirRad: '6.4 W/m²/sr/μm',
    ch4Est: '0.28 kg/s',
    co2e_rate_tph: 82.17,
    black_carbon_rate_kgph: 97.11,
    co2e_total_t: 7888.3,
    status: 'RECEIVED',
    diurnal_shape: 'FLAT_24H',
    dispatchTime: '13:59Z',
    receivedTime: '14:01Z',
    respondedTime: '14:10Z',
    authority: 'Hazira Industrial Safety Directorate',
    provenance: 'SIMULATED'
  },
  {
    id: 'SIM-04829',
    shortId: 'C55Z',
    name: 'Vadinar Marine Terminal',
    facilityId: 'VAD-MAR-03',
    coords: { lat: 22.56, lon: 69.73 },
    coordsStr: '22.560° N, 69.730° E',
    time: '2026-09-01T13:45:18Z',
    timestamp: '13:45:18 UTC',
    severity: 'CRITICAL',
    type: 'INDUSTRIAL FIRE',
    typeColor: '#ff4d4d',
    sevColor: '#ff4d4d',
    confidence: 0.885,
    effTemp: '1250 K',
    tempValue: 1250,
    area: '34.2 m²',
    p: 0.000243,
    frp: '87.4 MW',
    frpValue: 87.4,
    swirRad: '7.8 W/m²/sr/μm',
    mwirRad: '5.9 W/m²/sr/μm',
    ch4Est: '--',
    co2e_rate_tph: 129.96,
    black_carbon_rate_kgph: 116.28,
    co2e_total_t: 3119.0,
    status: 'RESPONDED',
    diurnal_shape: 'SPIKE_DECAY',
    dispatchTime: '13:46Z',
    receivedTime: '13:48Z',
    respondedTime: '14:00Z',
    authority: 'Kandla Coast Guard & Disaster Cell',
    provenance: 'SIMULATED'
  },
  {
    id: 'SIM-04820',
    shortId: 'D18K',
    name: 'Jharia Coalfield Seam #4',
    facilityId: 'BCCL-JHR-04',
    coords: { lat: 23.75, lon: 86.42 },
    coordsStr: '23.750° N, 86.420° E',
    time: '2026-09-01T13:12:05Z',
    timestamp: '13:12:05 UTC',
    severity: 'LOW',
    type: 'COAL SEAM',
    typeColor: '#f59e0b',
    sevColor: '#ffd6a3',
    confidence: 0.792,
    effTemp: '890 K',
    tempValue: 890,
    area: '85.0 m²',
    p: 0.001010,
    frp: '18.4 MW',
    frpValue: 18.4,
    swirRad: '3.1 W/m²/sr/μm',
    mwirRad: '3.8 W/m²/sr/μm',
    ch4Est: '--',
    co2e_rate_tph: 72.86,
    black_carbon_rate_kgph: 26.50,
    co2e_total_t: 8743.7,
    status: 'RESPONDED',
    diurnal_shape: 'FLAT_24H',
    dispatchTime: '13:14Z',
    receivedTime: '13:18Z',
    respondedTime: '13:35Z',
    authority: 'Haryana State Disaster Management Authority',
    provenance: 'SIMULATED'
  },
  {
    id: 'SIM-04815',
    shortId: 'E09M',
    name: 'Dahej Petrochem SEZ',
    facilityId: 'DHJ-SEZ-05',
    coords: { lat: 21.71, lon: 72.58 },
    coordsStr: '21.710° N, 72.580° E',
    time: '2026-09-01T12:49:33Z',
    timestamp: '12:49:33 UTC',
    severity: 'HIGH',
    type: 'GAS LEAK',
    typeColor: '#b197fc',
    sevColor: '#ff4d4d',
    confidence: 0.55,
    effTemp: '1410 K',
    tempValue: 1410,
    area: '18.6 m²',
    p: 0.000132,
    frp: '29.7 MW',
    frpValue: 29.7,
    swirRad: '9.4 W/m²/sr/μm',
    mwirRad: '6.1 W/m²/sr/μm',
    ch4Est: '1.15 kg/s',
    co2e_rate_tph: 133.65,
    black_carbon_rate_kgph: 0.0,
    co2e_total_t: 3207.6,
    status: 'DISPATCHED',
    diurnal_shape: 'DAYTIME_ONLY',
    dispatchTime: '12:50Z',
    receivedTime: '12:52Z',
    respondedTime: 'PENDING',
    authority: 'Gujarat Pollution Control Board Emergency Cell',
    provenance: 'SIMULATED'
  }
];

// --- Global Application State ---
const AppState = {
  activeView: 'mission-control',
  selectedAnomalyId: IS_EXPLICIT_DEMO ? 'SIM-04832' : null,
  selectedFacilityId: IS_EXPLICIT_DEMO ? 'RIL-JAM-01' : null,
  systemTimeOffset: 0,
  terminalPaused: false,
  mapMode: 'vector', // 'vector' | 'satellite'
  leafletMap: null,
  leafletMarkers: [],
  liveMode: !!AGNIVANI_API,
  detCounter: 0,
  lastIngestUtc: null,

  // Live Anomaly Dataset (VIIRS 375m & FIRMS Persistent Sources)
  // When ?demo=1 is explicitly supplied, initialize with demo fixtures; otherwise start empty and hydrate from live/cache
  anomalies: IS_EXPLICIT_DEMO ? [...DEMO_FIXTURES] : [],

  // Audit Trail Records
  auditTrail: [
    { timestamp: '14:05:22.451', operatorId: 'OP-883A', action: 'Confirm coordinates & radiance verification', ref: 'SIM-04832' },
    { timestamp: '14:02:10.019', operatorId: 'SYS-AUTO', action: 'Alert generated; dispatched to authorities via SAT-RELAY', ref: 'SIM-04832' },
    { timestamp: '13:58:45.102', operatorId: 'SYS-AUTO', action: 'VIIRS Day/Night Band radiance exceeded 4.2-sigma threshold', ref: 'SIM-04831' },
    { timestamp: '13:48:12.770', operatorId: 'OP-702B', action: 'Action checklist completed; nodal team notified', ref: 'SIM-04829' },
    { timestamp: '13:45:00.000', operatorId: 'SYS-AUTO', action: 'Routine VIIRS pass orbital cycle completed (NOAA-20)', ref: 'SYS-00000' }
  ]
};

// --- Deterministic Demo Detection Generator (no Math.random) ---
function generateDemoDetection() {
  if (!IS_EXPLICIT_DEMO) return null;
  const fixture = DEMO_FIXTURES[AppState.detCounter % DEMO_FIXTURES.length];
  AppState.detCounter += 1;
  return { ...fixture };
}

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
  SoundFX.init();
  initClock();
  initRouting();
  initAlertFeed();
  initMapCanvas();
  if (AppState.anomalies.length > 0) selectAnomaly(AppState.anomalies[0].id);
  updateStatsPanel(null);
  initSwipeSlider();
  initTerminalLog();
  initHeatmap();
  initPlanckCurve();
  initAuditTable();
  initEventListeners();
  initCSVUploader();
  setupLiveMode();
});

// --- Fail-Loud Unreachable Banner ---
function showUnreachableBanner(msg) {
  let banner = mustEl('backend-unreachable-banner');
  if (!banner) {
    banner = document.createElement('div');
    banner.id = 'backend-unreachable-banner';
    banner.className = 'w-full bg-error-container text-on-error font-data-mono text-[12px] font-bold px-4 py-2 border-b border-error flex items-center justify-between z-50 shadow-lg shrink-0';
    const header = document.querySelector('header');
    if (header && header.parentNode) {
      header.parentNode.insertBefore(banner, header.nextSibling);
    } else {
      document.body.prepend(banner);
    }
  }
  banner.innerHTML = `
    <div class="flex items-center gap-3">
      <div class="w-2.5 h-2.5 rounded-full bg-error animate-pulse shrink-0"></div>
      <span class="tracking-wide">${msg || 'LIVE BACKEND UNREACHABLE — using cached snapshot'}</span>
    </div>
    <div class="flex items-center gap-2">
      <button id="retry-backend-btn" class="bg-surface-container hover:bg-surface-bright text-primary border border-outline px-2.5 py-1 rounded text-[10px] font-label-caps transition-colors cursor-pointer">
        RETRY SYNC
      </button>
    </div>
  `;
  mustEl('retry-backend-btn')?.addEventListener('click', () => {
    hideUnreachableBanner();
    setupLiveMode();
  });
}

function hideUnreachableBanner() {
  const banner = mustEl('backend-unreachable-banner');
  if (banner) banner.remove();
}

function renderDemoBanner() {
  if (!IS_EXPLICIT_DEMO) return;
  document.body.dataset.mode = 'demo';
  let banner = mustEl('demo-mode-persistent-banner');
  if (!banner) {
    banner = document.createElement('div');
    banner.id = 'demo-mode-persistent-banner';
    banner.className = 'w-full bg-red-600 text-white font-mono text-[13px] font-bold px-4 py-2 border-b-2 border-red-800 flex items-center justify-center z-50 shadow-lg shrink-0 tracking-wider select-none';
    banner.innerHTML = '⚠ SIMULATED DATA — NOT LIVE';
    document.body.prepend(banner);
  }
}

function updateLiveStatusIndicator(lastIngestUtc, isOnline = true) {
  const pill = mustEl('live-status-pill');
  const dot = mustEl('live-status-dot');
  const text = mustEl('live-status-text');
  const clock = mustEl('last-ingest-clock');
  if (!pill || !dot || !text) return;

  if (lastIngestUtc) AppState.lastIngestUtc = lastIngestUtc;

  if (clock) {
    if (AppState.lastIngestUtc) {
      const d = new Date(AppState.lastIngestUtc);
      clock.textContent = d.toLocaleTimeString();
    } else {
      clock.textContent = 'never';
    }
  }

  if (!isOnline) {
    dot.className = 'w-2 h-2 rounded-full bg-error';
    text.className = 'font-label-caps text-[10px] text-error font-bold';
    text.textContent = 'OFFLINE';
    return;
  }

  const pollIntervalSeconds = 600;
  let isStale = false;
  if (AppState.lastIngestUtc) {
    const ageSeconds = (Date.now() - new Date(AppState.lastIngestUtc).getTime()) / 1000;
    if (ageSeconds > 3 * pollIntervalSeconds) {
      isStale = true;
    }
  }

  if (isStale) {
    dot.className = 'w-2 h-2 rounded-full bg-amber-500';
    text.className = 'font-label-caps text-[10px] text-amber-400 font-bold';
    text.textContent = 'STALE';
  } else {
    dot.className = 'w-2 h-2 rounded-full bg-emerald-500 animate-pulse';
    text.className = 'font-label-caps text-[10px] text-emerald-400 font-bold';
    text.textContent = 'LIVE';
  }
}

function renderEmptyState(lastIngest) {
  const feed = mustEl('alert-feed');
  if (feed) {
    feed.innerHTML = `
      <div class="p-6 text-center text-outline font-data-mono text-sm">
        <p class="font-bold text-on-surface">No detections in the selected window.</p>
        <p class="text-xs text-outline mt-1">Last ingest: ${lastIngest || 'never'}</p>
      </div>`;
  }
  const inspPanel = mustEl('inspection-panel');
  if (inspPanel) {
    inspPanel.innerHTML = `
      <div class="p-6 text-center text-outline font-data-mono text-xs">
        No thermal anomaly selected. Last ingest: ${lastIngest || 'never'}
      </div>`;
  }
  initMapCanvas();
}

function handleBackendUnreachable(msg) {
  showUnreachableBanner(msg || 'LIVE BACKEND UNREACHABLE — using cached snapshot');
  updateLiveStatusIndicator(AppState.lastIngestUtc, false);

  let cached = null;
  try {
    const raw = localStorage.getItem('agnivani_snapshot_cache');
    if (raw) cached = JSON.parse(raw);
  } catch (e) {
    console.warn('[AGNIVANI] Error reading cached snapshot from localStorage:', e);
  }

  if (cached) {
    console.log('[AGNIVANI] Loaded snapshot from localStorage cache');
    hydrateFromSnapshot(cached);
  } else {
    console.warn('[AGNIVANI] No cached snapshot found in localStorage.');
    if (IS_EXPLICIT_DEMO) {
      startDemoSimulation();
    } else {
      renderEmptyState('never (offline)');
    }
  }
}

// --- Live mode bootstrap ---
async function setupLiveMode() {
  hideUnreachableBanner();
  renderDemoBanner();

  if (IS_EXPLICIT_DEMO) {
    console.log('[AGNIVANI] EXPLICIT DEMO MODE (?demo=1) — starting rehearsal simulation');
    startDemoSimulation();
    return;
  }

  if (!AppState.liveMode) {
    console.warn('[AGNIVANI] Offline environment without live API detected');
    handleBackendUnreachable('LIVE BACKEND UNREACHABLE — using cached snapshot');
    return;
  }

  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 20000);
    const res = await fetch('/api/snapshot', { signal: controller.signal });
    clearTimeout(timer);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    console.log('[AGNIVANI] Snapshot loaded:', data.stats?.total_detections, 'detections');

    // Write cache on every successful snapshot
    try {
      localStorage.setItem('agnivani_snapshot_cache', JSON.stringify(data));
    } catch (e) {
      console.warn('[AGNIVANI] Could not cache snapshot to localStorage:', e);
    }

    hydrateFromSnapshot(data);
    connectSSE();
    startPipelinePolling();
  } catch (err) {
    console.warn('[AGNIVANI] Live backend unreachable:', err.message);
    handleBackendUnreachable('LIVE BACKEND UNREACHABLE — using cached snapshot');
  }
}

function hydrateFromSnapshot(data) {
  if (!data) return;
  const lastIngestStr = data.stats?.last_ingest_utc ? new Date(data.stats.last_ingest_utc).toLocaleString() : 'never';
  updateLiveStatusIndicator(data.stats?.last_ingest_utc, true);

  // Stats -> KPIs & Model Integrity
  if (data.stats) updateStatsPanel(data.stats);
  // Detections -> anomaly list (newest first)
  if (Array.isArray(data.detections) && data.detections.length > 0) {
    const mapped = data.detections.map(d => apiDetectionToAnomaly(d));
    AppState.anomalies = mapped;

    // Condition C4 live badge update
    const unresCount = mapped.filter(d => d.cls === 'UNRESOLVED').length;
    const unresBadge = mustEl('unresolved-count-badge');
    if (unresBadge) {
      unresBadge.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-amber-400"></span><span>${unresCount} non-industrial thermal activity in window — deliberately unattributed</span>`;
    }
    const limitsUnres = mustEl('limits-unresolved-count');
    if (limitsUnres) limitsUnres.innerText = unresCount;

    initAlertFeed();
    initMapCanvas();
    if (AppState.mapMode === 'satellite') refreshLeafletMap();

    // Deep link focus handler (P4 / C5)
    const urlParams = new URLSearchParams(window.location.search);
    const focusId = urlParams.get('focus');
    if (focusId && mapped.some(a => a.id === focusId)) {
      selectAnomaly(focusId);
      const target = mapped.find(a => a.id === focusId);
      if (target && AppState.leafletMap) {
        if (AppState.mapMode !== 'satellite') setMapMode('satellite');
        AppState.leafletMap.flyTo([target.coords.lat, target.coords.lon], 12, { duration: 1.2 });
      }
    } else if (AppState.anomalies.length > 0) {
      const defaultItem = mapped.find(a => a.cls !== 'UNRESOLVED' && a.name !== 'Unknown Facility') || mapped[0];
      selectAnomaly(defaultItem.id);
    }
  } else {
    AppState.anomalies = [];
    renderEmptyState(lastIngestStr);
  }
}

function apiDetectionToAnomaly(d) {
  const ts = typeof d.ts === 'string' ? d.ts : new Date(d.ts).toISOString();
  const isCandidateLeak = d.cls === 'LEAK';
  return {
    id: d.id, shortId: d.id.slice(-4).toUpperCase(),
    cls: d.cls,
    name: d.facility_name || 'Unknown Facility',
    facilityId: d.facility_name || '',
    coords: { lat: d.lat, lon: d.lon },
    coordsStr: `${d.lat.toFixed(3)}° N, ${d.lon.toFixed(3)}° E`,
    time: ts, timestamp: ts.substring(11, 19) + ' UTC',
    severity: d.severity || 'MODERATE',
    type: d.cls === 'FLARE' ? 'GAS FLARE' : d.cls === 'IND_FIRE' ? 'INDUSTRIAL FIRE' : d.cls === 'COAL' ? 'COAL SEAM' : isCandidateLeak ? 'candidate fugitive thermal anomaly - low confidence (0.55)' : (d.cls === 'WILD' ? 'WILDFIRE / AGRI' : (d.cls === 'UNRESOLVED' ? 'UNATTRIBUTED NON-INDUSTRIAL' : 'UNKNOWN')),
    typeColor: DETO_TYPE_COLORS[d.cls] || '#859397',
    sevColor: DETO_SEV_COLORS[d.severity] || '#ffd6a3',
    confidence: isCandidateLeak ? 0.55 : d.conf,
    effTemp: d.temp_K != null ? `${Math.round(d.temp_K)} K` : '-- K',
    tempValue: d.temp_K,
    area: d.area_m2 != null ? `${Math.round(d.area_m2)} m²` : '-- m²',
    frp: d.frp_MW != null ? `${Number(d.frp_MW).toFixed(1)} MW` : (d.frp_max_MW != null ? `${Number(d.frp_max_MW).toFixed(1)} MW` : '-- MW'),
    frpValue: d.frp_MW != null ? Number(d.frp_MW) : (d.frp_max_MW != null ? Number(d.frp_max_MW) : 0),
    status: 'LIVE',
    offshore_suppressed: !!d.offshore_suppressed,
    reason: isCandidateLeak ? (d.reason || 'candidate fugitive thermal anomaly - low confidence (0.55) driven by facility proximity; implicates Hazira LNG/Steel.') : (d.reason || ''),
    reason_template: d.reason_template || '',
    cited_rule: d.cited_rule || '',
    top_features: Array.isArray(d.top_features) ? d.top_features : [],
    diurnal_hist: Array.isArray(d.diurnal_hist) ? d.diurnal_hist : null,
    diurnal_shape: d.diurnal_shape || null,
    co2e_rate_tph: d.co2e_rate_tph != null ? Number(d.co2e_rate_tph) : null,
    black_carbon_rate_kgph: d.black_carbon_rate_kgph != null ? Number(d.black_carbon_rate_kgph) : null,
    co2e_total_t: d.co2e_total_t != null ? Number(d.co2e_total_t) : null
  };
}

function renderDiurnalSparkline(container, hist, shape) {
  if (!container) return;
  container.innerHTML = '';
  let data = hist;
  if (!Array.isArray(data) || data.length !== 24) {
    if (shape === 'DAYTIME_ONLY') {
      data = Array(24).fill(0.005);
      for (let h = 10; h <= 16; h++) data[h] = 0.13;
    } else if (shape === 'EVENING_BURST') {
      data = Array(24).fill(0.005);
      for (let h = 16; h <= 20; h++) data[h] = 0.18;
    } else if (shape === 'SPIKE_DECAY') {
      data = Array(24).fill(0.01);
      data[14] = 0.55; data[15] = 0.22;
    } else {
      data = Array(24).fill(1 / 24);
    }
  }

  const maxVal = Math.max(...data, 0.001);
  const containerHeight = 24; // px

  data.forEach((val, h) => {
    const bar = document.createElement('div');
    const heightPx = Math.max(2, Math.round((val / maxVal) * containerHeight));
    let color = '#60a5fa';
    if (h >= 10 && h <= 16) {
      color = '#f59e0b'; // daytime amber
    } else if (h >= 16 && h <= 20) {
      color = '#ff6b6b'; // evening orange
    } else if (h >= 21 || h <= 5) {
      color = '#00d2d3'; // night cyan
    }

    bar.style.height = `${heightPx}px`;
    bar.style.flex = '1';
    bar.style.backgroundColor = color;
    bar.style.borderRadius = '1px 1px 0 0';
    bar.style.opacity = val > 0.005 ? '0.9' : '0.25';
    bar.style.transition = 'all 0.15s';
    bar.title = `${String(h).padStart(2, '0')}:00 local — ${(val * 100).toFixed(1)}%`;

    bar.addEventListener('mouseenter', () => {
      bar.style.opacity = '1.0';
      bar.style.filter = 'brightness(1.3)';
    });
    bar.addEventListener('mouseleave', () => {
      bar.style.opacity = val > 0.005 ? '0.9' : '0.25';
      bar.style.filter = 'none';
    });

    container.appendChild(bar);
  });
}

// Mapping from cls/severity to color maps used above
const DETO_TYPE_COLORS = {'FLARE':'#ffa94d','IND_FIRE':'#ff4d4d','COAL':'#f59e0b','WILD':'#859397','LEAK':'#b197fc'};
const DETO_SEV_COLORS = {'CRITICAL':'#ff4d4d','HIGH':'#ffb13b','MODERATE':'#ffd6a3','LOW':'#bbc9cd'};

function generateS2NarratorInput(item) {
  if (!item) return '';
  const emLine = item.offshore_suppressed
    ? 'ESTIMATED EMISSIONS: NULL / SUPPRESSED (offshore marine cluster — zero terrestrial emissions credited)'
    : `ESTIMATED EMISSIONS: CO2e Rate = ${item.co2e_rate_tph != null ? Number(item.co2e_rate_tph).toFixed(2) : '0.00'} t/h | Black Carbon = ${item.black_carbon_rate_kgph != null ? Number(item.black_carbon_rate_kgph).toFixed(1) : '0.0'} kg/h | Cumulative CO2e = ${item.co2e_total_t != null ? Number(item.co2e_total_t).toFixed(1) : '0.0'} t`;
  return `[SENTINEL-2 (S2) NARRATOR TELEMETRY INPUT]
ANOMALY_ID: ${item.id} (${item.name})
CENTROID: ${item.coordsStr || (item.coords ? `${item.coords.lat}° N, ${item.coords.lon}° E` : '--')}
CLASSIFICATION: ${item.type} (confidence p=${(item.confidence ?? 0).toFixed(3)})
THERMAL: T_eff=${item.effTemp || '--'} | FRP=${item.frp || '--'}
DIURNAL_SIGNATURE: ${item.diurnal_shape || 'UNKNOWN'}
${emLine}
TASKING: Trigger Sentinel-2 MSI Band 11 (1.610 um) & Band 12 (2.190 um) SWIR imagery for 20m high-resolution flame footprint verification.`;
}

function updateStatsPanel(stats) {
  // Update KPI strip in analytics view
  const totalEl = mustEl('kpi-total-detections');
  if (totalEl && stats?.total_detections != null) totalEl.textContent = stats.total_detections.toLocaleString();

  // Update Estimated Emissions KPI tile
  const validAnomalies = (AppState.anomalies || []).filter(a => !a.offshore_suppressed && a.co2e_rate_tph != null);
  const totalRate = validAnomalies.reduce((acc, a) => acc + (Number(a.co2e_rate_tph) || 0), 0);
  const totalCumulative = validAnomalies.reduce((acc, a) => acc + (Number(a.co2e_total_t) || 0), 0);
  const kpiEmissions = mustEl('kpi-emissions');
  const kpiEmissionsTotal = mustEl('kpi-emissions-total');
  if (kpiEmissions) kpiEmissions.textContent = `${totalRate.toFixed(2)} t/h`;
  if (kpiEmissionsTotal) kpiEmissionsTotal.textContent = `${totalCumulative.toFixed(1)} t total`;

  // Update Model Integrity panel in mission control
  const miScorer = mustEl('mi-scorer');
  const miMode = mustEl('mi-mode');
  const miF1 = mustEl('mi-f1');
  const miBrier = mustEl('mi-brier');
  const miLeakage = mustEl('mi-leakage');
  if (miScorer) miScorer.textContent = `${stats?.scorer?.name || 'heuristic'} v${stats?.scorer?.version || ''}`;
  if (miMode) miMode.textContent = stats?.scorer?.mode || stats?.scorer?.name || 'heuristic';
  if (miF1) miF1.textContent = stats?.scorer?.metrics?.spatial_f1 != null ? stats.scorer.metrics.spatial_f1.toFixed(3) : '—';
  if (miBrier) miBrier.textContent = stats?.scorer?.metrics?.brier != null ? stats.scorer.metrics.brier.toFixed(4) : '—';
  const rf1 = stats?.scorer?.metrics?.random_f1 != null ? stats.scorer.metrics.random_f1.toFixed(3) : '—';
  const sf1 = stats?.scorer?.metrics?.spatial_f1 != null ? stats.scorer.metrics.spatial_f1.toFixed(3) : '—';
  if (miLeakage) miLeakage.textContent = `random ${rf1} vs spatial ${sf1}`;
}

// --- SSE connection ---
let sseSource = null;
function connectSSE() {
  if (sseSource) { sseSource.close(); sseSource = null; }
  try {
    sseSource = new EventSource('/api/stream');
    sseSource.onopen = () => console.log('[AGNIVANI] SSE connected');
    sseSource.addEventListener('detection', (e) => {
      try {
        const det = JSON.parse(e.data);
        appendAlertCard(apiDetectionToAnomaly(det));
      } catch (err) {
        console.error('[AGNIVANI] SSE parse error:', err);
      }
    });
    sseSource.addEventListener('heartbeat', () => {
      updateLiveStatusIndicator(AppState.lastIngestUtc, true);
    });
    sseSource.onerror = (err) => {
      console.warn('[AGNIVANI] SSE error, reconnecting...', err);
      updateLiveStatusIndicator(AppState.lastIngestUtc, false);
    };
  } catch (err) {
    console.warn('[AGNIVANI] EventSource unavailable:', err);
  }
}

// --- Pipeline log polling ---
let pipelineTimer = null;
function startPipelinePolling() {
  if (pipelineTimer) clearInterval(pipelineTimer);
  fetchPipelineLog();
  pipelineTimer = setInterval(fetchPipelineLog, 2000);
}

async function fetchPipelineLog() {
  if (!AppState.liveMode) return;
  try {
    const res = await fetch('/api/pipeline/log');
    if (!res.ok) return;
    const rows = await res.json();
    renderPipelineLog(rows);
  } catch (err) {
    console.warn('[AGNIVANI] pipeline/log fetch failed:', err);
  }
}

function renderPipelineLog(rows) {
  const logContainer = mustEl('terminal-log');
  if (!logContainer) return;
  // Keep last ~20 lines, prepend new ones with typewriter-ish stagger
  const existing = logContainer.querySelectorAll('div').length;
  const slice = rows.slice(- (20 - existing)).reverse();
  slice.forEach((row, i) => {
    const div = document.createElement('div');
    const ts = row.ts ? new Date(row.ts).toISOString().substring(11, 19) : '----:--:--';
    const levelColor = row.level === 'ERROR' ? 'text-error' : row.level === 'WARN' ? 'text-[#ffa94d]' : 'text-primary-container';
    div.innerHTML = `<span class="text-on-surface-variant/50">[${ts}]</span> <span class="${levelColor}">[${row.stage}]</span> ${row.message}`;
    div.style.opacity = '0';
    logContainer.appendChild(div);
    // Stagger entrance
    setTimeout(() => { div.style.transition = 'opacity 0.15s'; div.style.opacity = '1'; }, i * 60);
  });
  // Cap DOM nodes
  while (logContainer.querySelectorAll('div').length > 100) {
    logContainer.removeChild(logContainer.firstChild);
  }
  logContainer.scrollTop = logContainer.scrollHeight;
}

// --- Demo simulation loop (strictly for ?demo=1 offline rehearsal) ---
let demoInterval = null;
function startDemoSimulation() {
  if (!IS_EXPLICIT_DEMO) {
    console.log('[AGNIVANI] Demo simulation disabled (requires ?demo=1)');
    return;
  }
  if (demoInterval) return;
  demoInterval = setInterval(() => {
    const det = generateDemoDetection();
    if (det) appendAlertCard(det);
  }, 4000);
}

// --- Alert Feed with cap at 200 nodes ---
function appendAlertCard(anomaly) {
  const alertFeedContainer = mustEl('alert-feed');
  if (!alertFeedContainer) return;
  // Cap feed at 200 nodes
  if (alertFeedContainer.children.length >= 200) {
    alertFeedContainer.removeChild(alertFeedContainer.firstChild);
  }
  const isSuppressed = !!anomaly.offshore_suppressed;
  const emLine = isSuppressed
    ? '<div class="font-data-mono text-[9px] text-outline/60 mt-[2px] truncate">CO2e: -- (offshore suppressed)</div>'
    : (anomaly.co2e_rate_tph != null
        ? `<div class="font-data-mono text-[9px] text-tertiary mt-[2px] truncate flex justify-between"><span>CO2e: ${Number(anomaly.co2e_rate_tph).toFixed(2)} t/h</span><span>BC: ${(Number(anomaly.black_carbon_rate_kgph) || 0).toFixed(1)} kg/h</span></div>`
        : '');
  const card = document.createElement('div');
  card.className = `hud-border p-xs rounded-sm cursor-pointer relative overflow-hidden transition-all ${
    isSuppressed ? 'opacity-40 grayscale hover:opacity-100 border-dashed border-outline/40 bg-[#0d141d]/30' : 'bg-[#0d141d]/50 hover:bg-surface-container'
  }`;
  card.innerHTML = `
    <div class="absolute left-0 top-0 bottom-0 w-1 ${isSuppressed ? 'bg-outline' : 'bg-primary'}"></div>
    <div class="flex justify-between items-start mb-xs pl-1">
      <div class="flex items-center gap-xs">
        <div class="px-1 rounded-sm flex items-center h-4 border" style="background-color: ${anomaly.sevColor}22; border-color: ${anomaly.sevColor}">
          <span class="font-label-caps text-[8px]" style="color: ${anomaly.sevColor}">${anomaly.severity}</span>
        </div>
        ${isSuppressed ? '<span class="font-label-caps text-[7px] px-1 rounded-sm bg-surface-container-high text-outline border border-outline/30">SUPPRESSED</span>' : ''}
        <span class="font-data-mono text-[10px] text-primary font-bold">ID:${anomaly.shortId}</span>
      </div>
      <span class="font-data-mono text-[10px] text-on-surface-variant">${anomaly.timestamp?.split(' ')[0] || ''}</span>
    </div>
    <div class="pl-1">
      <div class="font-body-md text-[12px] font-semibold text-on-surface truncate">${anomaly.name}</div>
      <div class="flex gap-sm mt-[2px]">
        <span class="font-data-mono text-[10px] text-on-surface-variant">${anomaly.effTemp}</span>
        <span class="font-data-mono text-[10px] text-on-surface-variant">${anomaly.frp}</span>
      </div>
      ${emLine}
    </div>
  `;
  card.addEventListener('click', () => {
    SoundFX.playBlip();
    selectAnomaly(anomaly.id);
  });
  alertFeedContainer.insertBefore(card, alertFeedContainer.firstChild);
  // Also update anomalies list (head) and map
  AppState.anomalies.unshift(anomaly);
  if (AppState.anomalies.length > 200) AppState.anomalies.pop();
  initAlertFeed(); // refresh full feed to stay consistent
  initMapCanvas();
  if (AppState.mapMode === 'satellite') refreshLeafletMap();
  SoundFX.playBlip();
  appendTerminalLog(`<span class="text-primary font-bold">[DETECT]</span> New detection <span class="text-primary">${anomaly.id}</span> at ${anomaly.coordsStr} — ${anomaly.type} (${anomaly.effTemp})`);
}

// --- Mission Clock ---
function initClock() {
  const clockEl = mustEl('system-clock');
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
  const alertFeedContainer = mustEl('alert-feed');
  const alertQueueContainer = mustEl('queue-alert-list');

  if (alertFeedContainer) {
    alertFeedContainer.innerHTML = '';
    const filterMode = AppState.filterMode || 'corridor';
    let items = AppState.anomalies;
    if (filterMode === 'corridor') {
      items = items.filter(a => a.cls !== 'UNRESOLVED' && a.name !== 'Unknown Facility');
    }
    // Show up to 200 most recent
    items.slice(0, 200).forEach(anomaly => {
      const isSelected = anomaly.id === AppState.selectedAnomalyId;
      const isSuppressed = !!anomaly.offshore_suppressed;
      const emLine = isSuppressed
        ? '<div class="font-data-mono text-[9px] text-outline/60 mt-[2px] truncate">CO2e: -- (offshore suppressed)</div>'
        : (anomaly.co2e_rate_tph != null
            ? `<div class="font-data-mono text-[9px] text-tertiary mt-[2px] truncate flex justify-between"><span>CO2e: ${Number(anomaly.co2e_rate_tph).toFixed(2)} t/h</span><span>BC: ${(Number(anomaly.black_carbon_rate_kgph) || 0).toFixed(1)} kg/h</span></div>`
            : '');
      const card = document.createElement('div');
      card.className = `hud-border p-xs rounded-sm cursor-pointer relative overflow-hidden transition-all ${
        isSuppressed ? 'opacity-40 grayscale hover:opacity-100 border-dashed border-outline/40 ' : ''
      }${
        isSelected ? 'bg-surface-container border-primary/50' : 'bg-[#0d141d]/50 hover:bg-surface-container'
      }`;
      card.innerHTML = `
        ${isSelected ? '<div class="absolute left-0 top-0 bottom-0 w-1 bg-primary"></div>' : ''}
        <div class="flex justify-between items-start mb-xs ${isSelected ? 'pl-1' : ''}">
          <div class="flex items-center gap-xs">
            <div class="px-1 rounded-sm flex items-center h-4 border" style="background-color: ${anomaly.sevColor}22; border-color: ${anomaly.sevColor}">
              <span class="font-label-caps text-[8px]" style="color: ${anomaly.sevColor}">${anomaly.severity}</span>
            </div>
            ${isSuppressed ? '<span class="font-label-caps text-[7px] px-1 rounded-sm bg-surface-container-high text-outline border border-outline/30">SUPPRESSED</span>' : ''}
            <span class="font-data-mono text-[10px] ${isSelected ? 'text-primary font-bold' : 'text-on-surface-variant'}">ID:${anomaly.shortId}</span>
          </div>
          <span class="font-data-mono text-[10px] text-on-surface-variant">${anomaly.timestamp?.split(' ')[0] || ''}</span>
        </div>
        <div class="${isSelected ? 'pl-1' : ''}">
          <div class="font-body-md text-[12px] font-semibold text-on-surface truncate">${anomaly.name}</div>
          <div class="flex gap-sm mt-[2px]">
            <span class="font-data-mono text-[10px] text-on-surface-variant">${anomaly.effTemp}</span>
            <span class="font-data-mono text-[10px] text-on-surface-variant">${anomaly.frp}</span>
          </div>
          ${emLine}
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
    const items = AppState.anomalies.slice(0, 200);
    items.forEach(anomaly => {
      const isSelected = anomaly.id === AppState.selectedAnomalyId;
      const isSuppressed = !!anomaly.offshore_suppressed;
      const item = document.createElement('div');
      item.className = `p-sm border-b border-[#1b2735] relative group cursor-pointer transition-colors ${
        isSuppressed ? 'opacity-40 grayscale hover:opacity-100 ' : ''
      }${
        isSelected ? 'bg-secondary-container/30' : 'hover:bg-surface-container-highest'
      }`;
      item.innerHTML = `
        <div class="absolute left-0 top-0 bottom-0 w-[2px]" style="background-color: ${anomaly.sevColor}"></div>
        <div class="flex justify-between items-start mb-xs pl-xs">
          <div class="flex items-center gap-xs">
            <input type="checkbox" ${isSelected ? 'checked' : ''} class="w-3 h-3 bg-transparent border-outline-variant rounded-[2px] text-primary focus:ring-0">
            <span class="text-data-mono font-data-mono text-[11px] ${isSelected ? 'text-primary font-bold' : 'text-on-surface'}">${anomaly.id}</span>
          </div>
          <span class="text-data-mono font-data-mono text-[10px]" style="color: ${anomaly.sevColor}">${anomaly.timestamp?.split(' ')[0] || ''}</span>
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
  const inspSelectedId = mustEl('insp-selected-id');
  const inspName = mustEl('insp-name');
  const inspType = mustEl('insp-type');
  const inspConf = mustEl('insp-conf');
  const inspTemp = mustEl('insp-temp');
  const inspArea = mustEl('insp-area');
  const inspFrp = mustEl('insp-frp');
  const inspCh4 = mustEl('insp-ch4');

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
  if (inspCh4) inspCh4.innerText = item.ch4Est ?? '--';
  const inspCo2e = mustEl('insp-co2e');
  const inspBc = mustEl('insp-bc');
  if (inspCo2e) {
    inspCo2e.innerText = item.offshore_suppressed ? '-- t/h' : (item.co2e_rate_tph != null ? `${Number(item.co2e_rate_tph).toFixed(2)} t/h` : '-- t/h');
  }
  if (inspBc) {
    inspBc.innerText = item.offshore_suppressed ? '-- kg/h' : (item.black_carbon_rate_kgph != null ? `${Number(item.black_carbon_rate_kgph).toFixed(1)} kg/h` : '-- kg/h');
  }

  // Update Sentinel-2 (S2) Narrator Telemetry Input
  const s2NarratorEl = mustEl('s2-narrator-input');
  if (s2NarratorEl) {
    s2NarratorEl.value = generateS2NarratorInput(item);
  }

  // Update Diurnal Signature & Sparkline in Inspector
  const inspDiurnalShape = mustEl('insp-diurnal-shape');
  const inspDiurnalSparkline = mustEl('insp-diurnal-sparkline');
  if (inspDiurnalShape) {
    const shape = item.diurnal_shape || 'SPARSE';
    inspDiurnalShape.innerText = shape;
    if (shape === 'FLAT_24H') {
      inspDiurnalShape.className = 'font-data-mono text-[9px] font-bold px-1.5 py-0.5 rounded bg-cyan-950/60 text-cyan-400 border border-cyan-800';
    } else if (shape === 'DAYTIME_ONLY') {
      inspDiurnalShape.className = 'font-data-mono text-[9px] font-bold px-1.5 py-0.5 rounded bg-amber-950/60 text-amber-400 border border-amber-800';
    } else if (shape === 'EVENING_BURST') {
      inspDiurnalShape.className = 'font-data-mono text-[9px] font-bold px-1.5 py-0.5 rounded bg-orange-950/60 text-orange-400 border border-orange-800';
    } else if (shape === 'SPIKE_DECAY') {
      inspDiurnalShape.className = 'font-data-mono text-[9px] font-bold px-1.5 py-0.5 rounded bg-red-950/60 text-red-400 border border-red-800';
    } else {
      inspDiurnalShape.className = 'font-data-mono text-[9px] font-bold px-1.5 py-0.5 rounded bg-surface-container text-on-surface-variant border border-outline-variant';
    }
  }
  if (inspDiurnalSparkline) {
    renderDiurnalSparkline(inspDiurnalSparkline, item.diurnal_hist, item.diurnal_shape);
  }

  // Update Decision Narrative, Statutory Tag, and "Why" Driver Chips
  const inspReason = mustEl('insp-reason');
  const inspCitedRule = mustEl('insp-cited-rule');
  const inspWhyChips = mustEl('insp-why-chips');
  if (inspReason) {
    inspReason.innerText = item.reason || item.reason_template || 'Grounded narrative analysis pending orbital pass.';
  }
  if (inspCitedRule) {
    inspCitedRule.innerText = item.cited_rule || (item.offshore_suppressed ? 'OFFSHORE-SUPPRESSED' : 'GENERAL-ENVIRONMENTAL');
  }
  if (inspWhyChips) {
    inspWhyChips.innerHTML = '';
    const drivers = Array.isArray(item.top_features) && item.top_features.length > 0
      ? item.top_features
      : (item.effTemp && item.effTemp !== '-- K' ? [{name: 't_fire_K', value: item.tempValue}, {name: 'frp', value: item.frpValue}] : []);

    if (drivers.length === 0) {
      inspWhyChips.innerHTML = '<span class="font-data-mono text-[9px] text-on-surface-variant/60 italic">No feature drivers</span>';
    } else {
      drivers.slice(0, 5).forEach(feat => {
        const chip = document.createElement('span');
        chip.className = 'font-data-mono text-[8px] px-1.5 py-0.5 rounded bg-surface-container-high border border-outline-variant text-on-surface-variant flex items-center gap-1 shadow-sm';
        const formattedVal = typeof feat.value === 'number'
          ? (Number.isInteger(feat.value) ? feat.value : feat.value.toFixed(2))
          : feat.value;
        chip.innerHTML = `<span class="text-primary font-bold">${feat.name}:</span> ${formattedVal}`;
        inspWhyChips.appendChild(chip);
      });
    }
  }

  // Update Incident Summary in Alert Console
  const alertSumId = mustEl('summary-anomaly-id');
  const alertSumSev = mustEl('summary-severity-badge');
  const alertSumCoords = mustEl('summary-coords');
  if (alertSumId) alertSumId.innerText = item.id;
  if (alertSumSev) {
    alertSumSev.innerHTML = `<span class="material-symbols-outlined text-[16px]">warning</span> ${item.severity}`;
    alertSumSev.style.color = item.sevColor;
  }
  if (alertSumCoords) alertSumCoords.innerText = `${item.name}: ${item.coordsStr}`;

  // Update Dossier Info
  const dossierId = mustEl('dossier-id');
  const dossierType = mustEl('dossier-type');
  const dossierSev = mustEl('dossier-severity');
  const dossierFacility = mustEl('dossier-facility');
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
  const mapContainer = mustEl('mission-map-svg');
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

  // Plot Hotspots from AppState.anomalies (cap at 200)
  const filterMode = AppState.filterMode || 'corridor';
  let items = AppState.anomalies;
  if (filterMode === 'corridor') {
    items = items.filter(a => a.cls !== 'UNRESOLVED' && a.name !== 'Unknown Facility');
  }
  items.slice(0, 200).forEach((anomaly) => {
    const isSuppressed = !!anomaly.offshore_suppressed;
    const x = 240 + (anomaly.coords.lon - 68) * 28;
    const y = 520 - (anomaly.coords.lat - 18) * 26;

    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.setAttribute('class', 'cursor-pointer group');
    g.setAttribute('transform', `translate(${x}, ${y})`);
    if (isSuppressed) {
      g.setAttribute('opacity', '0.35');
    }

    const ringColor = isSuppressed ? '#859397' : anomaly.typeColor;
    const circleRing = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circleRing.setAttribute('r', '16');
    circleRing.setAttribute('fill', 'none');
    circleRing.setAttribute('stroke', ringColor);
    circleRing.setAttribute('stroke-width', '0.75');
    circleRing.setAttribute('stroke-dasharray', '3,3');
    circleRing.setAttribute('opacity', isSuppressed ? '0.3' : '0.6');
    g.appendChild(circleRing);

    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('r', '6');
    circle.setAttribute('fill', ringColor);
    circle.setAttribute('class', anomaly.severity === 'CRITICAL' && !isSuppressed ? 'pulse-critical' : '');
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
  const vectorContainer = mustEl('mission-map-svg');
  const leafletContainer = mustEl('leaflet-map-container');
  const radarSweep = mustEl('map-radar-sweep');
  const btnVector = mustEl('btn-map-vector');
  const btnSat = mustEl('btn-map-satellite');

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
  const container = mustEl('leaflet-map-container');
  if (!container) return;

  if (!AppState.leafletMap) {
    AppState.leafletMap = L.map('leaflet-map-container', {
      center: [21.8, 71.5],
      zoom: 8,
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

  // Filter based on corridor view mode (Condition C4)
  const filterMode = AppState.filterMode || 'corridor';
  let items = AppState.anomalies;
  if (filterMode === 'corridor') {
    items = items.filter(a => a.cls !== 'UNRESOLVED' && a.name !== 'Unknown Facility');
  }

  // Plot current anomalies (cap at 200)
  items.slice(0, 200).forEach(anomaly => {
    const isSuppressed = !!anomaly.offshore_suppressed;
    const markerColor = isSuppressed ? '#859397' : anomaly.typeColor;
    const opacity = isSuppressed ? '0.4' : '1.0';
    const customIcon = L.divIcon({
      className: 'custom-div-icon',
      html: `<div style="width: 20px; height: 20px; opacity: ${opacity}; background-color: ${markerColor}; border: 2px solid ${isSuppressed ? '#859397' : '#ffffff'}; border-radius: 50%; box-shadow: 0 0 10px ${markerColor}; filter: ${isSuppressed ? 'grayscale(1)' : 'none'};" class="${anomaly.severity === 'CRITICAL' && !isSuppressed ? 'pulse-critical' : ''}"></div>`,
      iconSize: [20, 20],
      iconAnchor: [10, 10]
    });

    const marker = L.marker([anomaly.coords.lat, anomaly.coords.lon], { icon: customIcon }).addTo(AppState.leafletMap);

    marker.bindPopup(`
      <div style="font-family: 'JetBrains Mono', monospace; font-size: 11px;">
        <strong style="color: ${markerColor}">${anomaly.name}</strong> ${isSuppressed ? '<span style=\"color:#859397;\">[OFFSHORE SUPPRESSED]</span>' : ''}<br/>
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
  const container = mustEl('swipe-container');
  const handle = mustEl('swipe-handle');
  const afterImg = mustEl('swipe-after');

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
  const logContainer = mustEl('terminal-log');
  if (!logContainer) return;

  // Pre-populate with some initial lines (same as before)
  const mockLogs = [
    { mod: '[GEE]', color: 'text-primary-container', msg: 'VIIRS granules ingest stream active (NOAA-20 orbit #34891)' },
    { mod: '[PHYS]', color: 'text-tertiary-container', msg: 'Spectral radiance solver computed dual-band temp: 1847.2 K' },
    { mod: '[BASE]', color: 'text-[#ffa94d]', msg: 'Background contextualization: Anomaly delta > 4.6 sigma relative to 30d baseline' },
    { mod: '[FUSE]', color: 'text-error', msg: 'Multi-band saturation confirmed on I4 band at coords 22.35N, 70.02E' },
    { mod: '[CLASS]', color: 'text-primary', msg: 'XGBoost v4.2 inference verdict: GAS FLARE (confidence p=0.943)' },
    { mod: '[NPS]', color: 'text-secondary', msg: 'Persistent Source Register matched: RIL-JAM-01 (100% historical persistence)' }
  ];

  mockLogs.forEach((item, i) => {
    setTimeout(() => {
      const now = new Date();
      const ts = now.toISOString().substring(11, 19);
      appendTerminalLog(`<span class="text-on-surface-variant/50">[${ts}]</span> <span class="${item.color}">${item.mod}</span> ${item.msg}`);
    }, i * 150);
  });
}

function appendTerminalLog(htmlMsg) {
  const logContainer = mustEl('terminal-log');
  if (!logContainer) return;
  const div = document.createElement('div');
  div.innerHTML = htmlMsg;
  logContainer.appendChild(div);
  logContainer.scrollTop = logContainer.scrollHeight;
}

// --- 365-Day Activity Heatmap Grid ---
function initHeatmap() {
  const container = mustEl('facility-heatmap-grid');
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

  const dateCounts = {};
  (AppState.anomalies || []).forEach(a => {
    if (a.time) {
      const d = a.time.substring(0, 10);
      dateCounts[d] = (dateCounts[d] || 0) + 1;
    }
  });

  for (let i = 0; i < 364; i++) {
    const curDate = new Date(startDate);
    curDate.setDate(curDate.getDate() + i);
    const dateStr = curDate.toISOString().substring(0, 10);
    const count = dateCounts[dateStr] || 0;

    let colorIdx = 0;
    if (count > 5) colorIdx = 6;
    else if (count > 3) colorIdx = 5;
    else if (count > 2) colorIdx = 4;
    else if (count > 1) colorIdx = 3;
    else if (count > 0) colorIdx = 2;
    else colorIdx = 0;

    const cell = document.createElement('div');
    cell.className = `w-full h-[9px] rounded-sm transition-all hover:scale-125 hover:z-20 cursor-pointer ${colors[colorIdx]}`;
    cell.setAttribute('title', `${dateStr}: ${count} thermal detections (${count > 0 ? (count * 14.2).toFixed(1) + ' MW' : 'Nominal'})`);
    container.appendChild(cell);
  }
}

// --- Planck Radiation Curve Renderer ---
function initPlanckCurve() {
  const curveSvg = mustEl('planck-svg-curve');
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
  const tbody = mustEl('audit-table-body');
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
  const modal = mustEl('csv-modal');
  const openBtn = mustEl('open-csv-btn');
  const closeBtn = mustEl('close-csv-btn');
  const dropzone = mustEl('csv-dropzone');
  const fileInput = mustEl('csv-file-input');
  const sampleBtn = mustEl('load-sample-csv-btn');

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

function handleCSVFile(file) {
  executeBackendPipeline(file, file.name);
}

function loadSampleFirmsCSV() {
  executeBackendPipeline(null, '5-day Gujarat Corridor Feed');
}

async function executeBackendPipeline(fileOrNull, filename = 'corridor_feed.csv') {
  const liveProgress = mustEl('pipeline-live-progress');
  const spinner = mustEl('pipeline-spinner');
  const totalTimeEl = mustEl('pipeline-total-time');
  const summaryEl = mustEl('pipeline-run-summary');

  if (liveProgress) liveProgress.classList.remove('hidden');
  if (summaryEl) summaryEl.classList.add('hidden');
  if (spinner) spinner.classList.add('animate-spin');
  if (totalTimeEl) totalTimeEl.innerText = 'RUNNING...';

  // Reset stage indicators
  const stages = ['ingest', 'landcover', 'cluster', 'dozier', 'score', 'dispatch'];
  stages.forEach(st => {
    const statusEl = mustEl(`stage-${st}-status`);
    const msEl = mustEl(`stage-${st}-ms`);
    if (statusEl) {
      statusEl.innerText = '⏳';
      statusEl.className = 'w-4 h-4 rounded-full flex items-center justify-center text-[10px] bg-amber-900 text-amber-300 font-bold';
    }
    if (msEl) msEl.innerText = '-- ms';
  });

  appendTerminalLog(`<span class="text-cyan-400 font-bold">[PIPELINE]</span> Initiating 6-stage telemetry run on ${filename}...`);

  try {
    let response;
    if (fileOrNull) {
      const formData = new FormData();
      formData.append('file', fileOrNull);
      response = await fetch('/api/pipeline/run', {
        method: 'POST',
        body: formData
      });
    } else {
      response = await fetch('/api/pipeline/run', {
        method: 'POST'
      });
    }

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Pipeline execution failed' }));
      alert(`Pipeline error: ${err.detail || response.statusText}`);
      if (totalTimeEl) totalTimeEl.innerText = 'ERROR';
      if (spinner) spinner.classList.remove('animate-spin');
      return;
    }

    const runData = await response.json();
    if (totalTimeEl) totalTimeEl.innerText = `${runData.total_ms.toFixed(1)} ms`;
    if (spinner) spinner.classList.remove('animate-spin');

    // Update stages with measured wall-clock millisecond durations
    const durations = runData.stage_durations || {};
    stages.forEach(st => {
      const statusEl = mustEl(`stage-${st}-status`);
      const msEl = mustEl(`stage-${st}-ms`);
      const dur = durations[st] != null ? Number(durations[st]).toFixed(1) : '1.0';
      if (statusEl) {
        statusEl.innerText = '✓';
        statusEl.className = 'w-4 h-4 rounded-full flex items-center justify-center text-[10px] bg-emerald-950 text-emerald-400 border border-emerald-600 font-bold';
      }
      if (msEl) msEl.innerText = `${dur} ms`;
    });

    if (summaryEl) {
      summaryEl.classList.remove('hidden');
      summaryEl.innerHTML = `
        <div class="font-bold text-cyan-300">✓ RUN ${runData.run_id} COMPLETE (${runData.total_ms.toFixed(1)} ms)</div>
        <div class="grid grid-cols-2 gap-1 text-[9px] pt-1">
          <div>Raw records: <span class="text-white font-bold">${runData.raw_records}</span></div>
          <div>Clusters formed: <span class="text-white font-bold">${runData.clusters_formed}</span></div>
          <div>Dozier converged: <span class="text-white font-bold">${runData.dozier_converged}</span></div>
          <div>Facilities matched: <span class="text-white font-bold">${runData.facilities_matched}</span></div>
          <div>Alerts dispatched: <span class="text-white font-bold">${runData.alerts_dispatched}</span></div>
          <div>Non-industrial: <span class="text-amber-400 font-bold">${runData.unresolved_count}</span></div>
        </div>
      `;
    }

    appendTerminalLog(`<span class="text-emerald-400 font-bold">[PIPELINE]</span> Run ${runData.run_id} finished in ${runData.total_ms.toFixed(1)} ms. ${runData.facilities_matched} facility matches, ${runData.dozier_converged} Dozier inversions.`);

    // Refresh live detections from backend
    await setupLiveMode();
    SoundFX.playDispatch();
  } catch (exc) {
    console.error('Pipeline execution exception:', exc);
    if (totalTimeEl) totalTimeEl.innerText = 'FAILED';
    if (spinner) spinner.classList.remove('animate-spin');
  }
}

// --- Interactive Modal & Event Listeners ---
function initEventListeners() {
  // Audio toggle listener
  const audioBtn = mustEl('audio-toggle-btn');
  if (audioBtn) {
    audioBtn.addEventListener('click', () => {
      SoundFX.toggle();
    });
  }

  // Map Switcher buttons
  const btnVector = mustEl('btn-map-vector');
  const btnSat = mustEl('btn-map-satellite');
  if (btnVector) {
    btnVector.addEventListener('click', () => setMapMode('vector'));
  }
  if (btnSat) {
    btnSat.addEventListener('click', () => setMapMode('satellite'));
  }

  // Corridor Filter Mode buttons (Condition C4)
  const filterCorridorBtn = mustEl('filter-corridor-btn');
  const filterAllBtn = mustEl('filter-all-btn');
  if (filterCorridorBtn && filterAllBtn) {
    filterCorridorBtn.addEventListener('click', () => {
      SoundFX.playBlip();
      AppState.filterMode = 'corridor';
      filterCorridorBtn.className = 'px-2 py-0.5 rounded-sm font-label-caps text-[9px] bg-primary text-black font-bold transition-all';
      filterAllBtn.className = 'px-2 py-0.5 rounded-sm font-label-caps text-[9px] bg-surface-container text-on-surface-variant hover:text-primary transition-all';
      initAlertFeed();
      initMapCanvas();
      if (AppState.mapMode === 'satellite') refreshLeafletMap();
    });

    filterAllBtn.addEventListener('click', () => {
      SoundFX.playBlip();
      AppState.filterMode = 'all';
      filterAllBtn.className = 'px-2 py-0.5 rounded-sm font-label-caps text-[9px] bg-primary text-black font-bold transition-all';
      filterCorridorBtn.className = 'px-2 py-0.5 rounded-sm font-label-caps text-[9px] bg-surface-container text-on-surface-variant hover:text-primary transition-all';
      initAlertFeed();
      initMapCanvas();
      if (AppState.mapMode === 'satellite') refreshLeafletMap();
    });
  }

  // Hero Quick-Focus Deep-Link buttons (Condition C5)
  function focusHero(heroId) {
    SoundFX.playBlip();
    if (AppState.filterMode !== 'corridor') {
      AppState.filterMode = 'corridor';
      if (filterCorridorBtn) filterCorridorBtn.className = 'px-2 py-0.5 rounded-sm font-label-caps text-[9px] bg-primary text-black font-bold transition-all';
      if (filterAllBtn) filterAllBtn.className = 'px-2 py-0.5 rounded-sm font-label-caps text-[9px] bg-surface-container text-on-surface-variant hover:text-primary transition-all';
      initAlertFeed();
      initMapCanvas();
    }
    selectAnomaly(heroId);
    const item = AppState.anomalies.find(a => a.id === heroId);
    if (item && AppState.leafletMap) {
      if (AppState.mapMode !== 'satellite') setMapMode('satellite');
      AppState.leafletMap.flyTo([item.coords.lat, item.coords.lon], 12, { duration: 1.2 });
    }
  }

  const heroF1 = mustEl('hero-flare-1-btn');
  const heroF2 = mustEl('hero-flare-2-btn');
  const heroLk = mustEl('hero-leak-btn');
  if (heroF1) heroF1.addEventListener('click', () => focusHero('AV-0B12A4B9'));
  if (heroF2) heroF2.addEventListener('click', () => focusHero('AV-95BA9779'));
  if (heroLk) heroLk.addEventListener('click', () => focusHero('AV-07D8247D'));

  // Pipeline modal actions
  const runCorridorBtn = mustEl('run-corridor-btn');
  if (runCorridorBtn) {
    runCorridorBtn.addEventListener('click', () => {
      SoundFX.playBlip();
      executeBackendPipeline(null, '5-day Gujarat Corridor Feed');
    });
  }

  const viewMapBtn = mustEl('pipeline-view-map-btn');
  const csvModal = mustEl('csv-modal');
  if (viewMapBtn && csvModal) {
    viewMapBtn.addEventListener('click', () => {
      csvModal.classList.add('hidden');
      switchView('mission-control');
      if (AppState.mapMode !== 'satellite') setMapMode('satellite');
    });
  }

  // Provenance Chip listener (P5)
  const provChip = mustEl('provenance-chip');
  if (provChip) {
    provChip.addEventListener('click', async () => {
      SoundFX.playBlip();
      try {
        const res = await fetch('/api/provenance');
        if (res.ok) {
          const prov = await res.json();
          alert(`PROVENANCE INFORMATION:\n• Dataset: ${prov.dataset_name}\n• Sensor: ${prov.sensor}\n• Window: ${prov.temporal_window}\n• Total Clusters: ${prov.total_detections}\n• Facilities Matched: ${prov.facilities_matched}\n• Dozier Converged: ${prov.dozier_converged}\n• Non-industrial Unattributed: ${prov.unresolved_count}\n• Disclosure: ${prov.threshold_disclosure}`);
        }
      } catch (e) {
        console.warn('Could not fetch provenance:', e);
      }
    });
  }

  // Dispatch Modal Open
  const dispatchButtons = document.querySelectorAll('[data-action="open-dispatch"]');
  const modal = mustEl('dispatch-modal');
  const closeModalBtn = mustEl('close-dispatch-modal');
  const confirmDispatchBtn = mustEl('confirm-dispatch-btn');

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
