import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Activity,
  Bell,
  CheckCircle2,
  ChevronRight,
  Clock,
  Database,
  FileText,
  LayoutDashboard,
  Layers,
  Play,
  Radar,
  RefreshCw,
  Settings,
  ShieldCheck,
  Sparkles,
  Square,
  Target,
  TrendingUp,
} from 'lucide-react';
import { usePipeline } from './usePipeline';
import { DriftChart } from './components/DriftChart';
import { ImportanceChart } from './components/ImportanceChart';
import { PerformanceChart } from './components/PerformanceChart';
import { ShadowArena } from './components/ShadowArena';
import './App.css';

const driftFallback = [
  { feature: 'type', psi: 0.42 },
  { feature: 'amount', psi: 0.37 },
  { feature: 'oldBalanceOrg', psi: 0.31 },
  { feature: 'newBalanceOrig', psi: 0.28 },
  { feature: 'oldBalanceDest', psi: 0.19 },
  { feature: 'newBalanceDest', psi: 0.12 },
];

const navItems = [
  { id: 'dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { id: 'drift', icon: Radar, label: 'Drift Radar' },
  { id: 'models', icon: Database, label: 'Model Registry' },
  { id: 'performance', icon: TrendingUp, label: 'Performance' },
  { id: 'alerts', icon: Bell, label: 'Alerts' },
  { id: 'logs', icon: FileText, label: 'Logs' },
];

const configItems = [
  { icon: Layers, label: 'Adapters' },
  { icon: Target, label: 'Scenarios' },
  { icon: Settings, label: 'Settings' },
];

const scenarioCards = [
  { id: 'night_shift', icon: Clock, label: 'Night Shift' },
  { id: 'high_value', icon: TrendingUp, label: 'High Value' },
];

const healthLabels: Record<string, { label: string; tone: string; dot: string }> = {
  healthy: { label: 'Healthy', tone: 'text-emerald-400', dot: 'bg-emerald-400' },
  warning: { label: 'Warning', tone: 'text-amber-400', dot: 'bg-amber-400' },
  critical: { label: 'Critical', tone: 'text-rose-400', dot: 'bg-rose-400' },
};

const formatClock = (value: string) =>
  new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

const formatActionLabel = (action: string) => {
  if (action === 'none') return 'monitoring';
  if (action === 'alert') return 'alert';
  if (action === 'shadow') return 'shadow trial';
  if (action === 'failed_retrain') return 'retrain failed';
  return action;
};

const formatLatency = (seconds: number | null) => {
  if (seconds === null || Number.isNaN(seconds)) return '--';
  if (seconds < 1) return `${Math.round(seconds * 1000)} ms`;
  return `${seconds.toFixed(2)} s`;
};

// Aggregate consecutive "none" actions into a single stability period entry
interface AggregatedHistoryEntry {
  iteration: number;
  timestamp: string;
  model_version: number | null;
  f1_score: number | null;
  drift_score: number;
  action: string;
  reason: string;
  isAggregated?: boolean;
  stableIterations?: number;
  timeDuration?: string;
  firstTimestamp?: string;
}

const aggregateStablePeriods = (history: any[]): AggregatedHistoryEntry[] => {
  if (history.length === 0) return [];

  const aggregated: AggregatedHistoryEntry[] = [];
  let i = 0;

  while (i < history.length) {
    const current = history[i];

    // If this is a "none" action, group all consecutive "none" entries
    if (current.action === 'none') {
      const groupStart = i;
      let groupEnd = i;

      // Find all consecutive "none" entries
      while (groupEnd < history.length && history[groupEnd].action === 'none') {
        groupEnd++;
      }

      const groupSize = groupEnd - groupStart;

      // Only aggregate if there are 3+ consecutive stable entries
      if (groupSize >= 3) {
        const firstEntry = history[groupStart];
        const lastEntry = history[groupEnd - 1];

        // Calculate time duration between first and last entry
        const firstTime = new Date(lastEntry.timestamp); // Last in list is earliest due to DESC order
        const lastTime = new Date(firstEntry.timestamp); // First in list is latest
        const durationMs = lastTime.getTime() - firstTime.getTime();
        const durationMins = Math.round(durationMs / 60000);

        let timeDurationStr = '';
        if (durationMins < 60) {
          timeDurationStr = `${durationMins}m`;
        } else {
          const hours = Math.floor(durationMins / 60);
          const mins = durationMins % 60;
          timeDurationStr = `${hours}h ${mins}m`;
        }

        aggregated.push({
          iteration: firstEntry.iteration,
          timestamp: firstEntry.timestamp,
          model_version: firstEntry.model_version,
          f1_score: firstEntry.f1_score,
          drift_score: firstEntry.drift_score,
          action: 'stable',
          reason: `Pipeline stable for ${groupSize} iterations (${timeDurationStr})`,
          isAggregated: true,
          stableIterations: groupSize,
          timeDuration: timeDurationStr,
          firstTimestamp: lastEntry.timestamp,
        });

        i = groupEnd;
      } else {
        // If fewer than 3, add them individually
        aggregated.push(current);
        i++;
      }
    } else {
      // Non-"none" entries are added as-is
      aggregated.push(current);
      i++;
    }
  }

  return aggregated;
};

const pageMeta: Record<string, { eyebrow: string; title: string; description: string }> = {
  dashboard: {
    eyebrow: 'Overview',
    title: 'Operations Dashboard',
    description: 'Live pipeline health, drift, registry status, and control actions.',
  },
  drift: {
    eyebrow: 'Drift Radar',
    title: 'Feature Stability',
    description: 'Focused drift analysis with the strongest PSI signals surfaced first.',
  },
  models: {
    eyebrow: 'Model Registry',
    title: 'Version History',
    description: 'Active model lineage, promotion order, and latest training status.',
  },
  performance: {
    eyebrow: 'Performance',
    title: 'Self-Healing Trend',
    description: 'F1 evolution, retrain points, and recent healing decisions over time.',
  },
  alerts: {
    eyebrow: 'Alerts',
    title: 'Health and Warnings',
    description: 'Non-happy-path events, drift alerts, and operational warnings.',
  },
  logs: {
    eyebrow: 'Logs',
    title: 'Recent Activity',
    description: 'Timeline of pipeline actions and the latest state changes.',
  },
};

const App: React.FC = () => {
  const { status, history, models, driftReports, metrics, loading, startPipeline, stopPipeline } = usePipeline();
  const [selectedAdapter, setSelectedAdapter] = useState('paysim');
  const [selectedScenario, setSelectedScenario] = useState('normal');
  const [activeNav, setActiveNav] = useState('dashboard');

  if (loading || !status) {
    return (
      <div className="app-loading">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 1.1, ease: 'linear' }}
          className="app-loading__spinner"
        >
          <Activity className="h-12 w-12 text-emerald-400" />
        </motion.div>
      </div>
    );
  }

  const activeModel = models.find((model) => model.is_active);
  const currentTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const f1Score = status.active_model_f1 ?? 0;
  const health = healthLabels[status.health] ?? healthLabels.healthy;
  const driftData = driftReports?.features?.length
    ? Object.fromEntries(
        driftReports.features.map((feature: { feature: string; psi_score: number }) => [feature.feature, feature.psi_score]),
      )
    : Object.fromEntries(driftFallback.map((entry) => [entry.feature, entry.psi]));
  const importanceData = activeModel?.feature_importance && Object.keys(activeModel.feature_importance).length > 0
    ? activeModel.feature_importance
    : {
        transaction_amount: 0.29,
        distance_from_home: 0.24,
        oldBalanceOrg: 0.18,
        newBalanceDest: 0.14,
        hour_of_day: 0.09,
        is_foreign: 0.06,
      };
  const sortedModels = [...models].sort((left, right) => right.version - left.version);
  const dashboardModels = sortedModels.slice(0, 5);
  const dashboardHistory = history.slice(0, 5);
  const dashboardDriftData = Object.fromEntries(Object.entries(driftData).slice(0, 6));
  const dashboardRecentFeatures = status.last_drifted_features.slice(0, 6);
  const recentHistory = history;
  const aggregatedHistory = aggregateStablePeriods(history);
  const driftCount = status.last_drifted_features.length;
  const latestEvent = dashboardHistory[0] ?? recentHistory[0];
  const page = pageMeta[activeNav] ?? pageMeta.dashboard;
  const alertHistory = history.filter((entry) => entry.action !== 'none');
  const driftedHistory = history.filter((entry) => entry.action === 'drift' || entry.action === 'alert' || entry.drift_score >= 0.1);
  const metricsFamilies = metrics?.metrics ?? [];
  const metricsFamilyCount = metricsFamilies.length;
  const metricsSampleCount = metricsFamilies.reduce((total, family) => total + family.samples.length, 0);
  const latencyFamily = metricsFamilies.find((family) => family.name === 'api_request_latency_seconds');
  const latencySamples = latencyFamily?.samples ?? [];
  const requestCount = latencySamples
    .filter((sample) => sample.name.endsWith('_count'))
    .reduce((total, sample) => total + sample.value, 0);
  const requestSum = latencySamples
    .filter((sample) => sample.name.endsWith('_sum'))
    .reduce((total, sample) => total + sample.value, 0);
  const averageLatencyMs = requestCount > 0 ? (requestSum / requestCount) * 1000 : null;

  return (
    <div className="app-shell">
      <div className="app-shell__glow app-shell__glow--one" />
      <div className="app-shell__glow app-shell__glow--two" />

      <aside className="app-sidebar">
        <div className="sidebar-brand">
          <div className="sidebar-brand__icon">
            <ShieldCheck className="h-6 w-6 text-cyan-300" />
          </div>
          <div>
            <div className="sidebar-brand__title">GUARDIAN</div>
            <div className="sidebar-brand__subtitle">Self-Healing MLOps</div>
          </div>
        </div>

        <div className="sidebar-group">
          <div className="sidebar-group__label">Mission Control</div>
          <div className="sidebar-nav">
            {navItems.map(({ id, icon: Icon, label }) => (
              <button
                key={id}
                type="button"
                onClick={() => setActiveNav(id)}
                className={`sidebar-nav__item ${activeNav === id ? 'sidebar-nav__item--active' : ''}`}
              >
                <Icon className="h-4 w-4" />
                <span>{label}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="sidebar-group">
          <div className="sidebar-group__label">Configuration</div>
          <div className="sidebar-nav">
            {configItems.map(({ icon: Icon, label }) => (
              <button key={label} type="button" className="sidebar-nav__item sidebar-nav__item--ghost">
                <Icon className="h-4 w-4" />
                <span>{label}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="sidebar-system">
          <div className="sidebar-group__label">System</div>
          <div className="stat-row">
            <span>Pipeline Uptime</span>
            <strong>2h 47m 15s</strong>
          </div>
          <div className="stat-row">
            <span>API Latency</span>
            <strong>128 ms</strong>
          </div>
          <div className="stat-row">
            <span>Backend Status</span>
            <strong className="stat-row__status">
              <span className={`stat-row__dot ${health.dot}`} />
              {health.label}
            </strong>
          </div>
        </div>
      </aside>

      <main className="app-main">
        <div className="dashboard-hero">
          <div>
            <div className="dashboard-hero__eyebrow">{page.eyebrow}</div>
            <h1 className="dashboard-hero__title">{page.title}</h1>
            <p className="dashboard-hero__description">{page.description}</p>
          </div>
          <div className="dashboard-hero__status">
            <span className={`status-pill__dot ${health.dot}`} />
            <span>{health.label}</span>
          </div>
        </div>

        <motion.div
          className="top-strip"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
        >
          <div className="metric-card">
            <div className="metric-card__label">Pipeline Status</div>
            <div className="metric-card__value-row">
              <span className={`metric-card__dot ${status.running ? 'metric-card__dot--live' : 'metric-card__dot--idle'}`} />
              <div className={`metric-card__value ${status.running ? 'metric-card__value--live' : 'metric-card__value--idle'}`}>
                {status.running ? 'RUNNING' : 'STOPPED'}
              </div>
            </div>
            <div className="metric-card__hint">All systems operational</div>
          </div>

          <div className="metric-card">
            <div className="metric-card__label">Current Iteration</div>
            <div className="metric-card__big-value">
              {status.iteration.toLocaleString()} <span>/ ∞</span>
            </div>
            <div className="metric-card__hint">Chunks processed</div>
          </div>

          <div className="metric-card">
            <div className="metric-card__label">Active Model</div>
            <div className="metric-card__big-value">v{status.active_model_version ?? '--'}</div>
            <div className="metric-card__hint metric-card__hint--success">Promoted 2 min ago</div>
          </div>

          <div className="metric-card metric-card--gauge">
            <div className="gauge">
              <svg className="gauge__ring" viewBox="0 0 120 120">
                <defs>
                  <linearGradient id="dashboardF1Gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#fde047" />
                    <stop offset="50%" stopColor="#34d399" />
                    <stop offset="100%" stopColor="#10b981" />
                  </linearGradient>
                </defs>
                <circle cx="60" cy="60" r="48" className="gauge__track" />
                <circle
                  cx="60"
                  cy="60"
                  r="48"
                  className="gauge__value"
                  style={{
                    stroke: 'url(#dashboardF1Gradient)',
                    strokeDasharray: `${2 * Math.PI * 48}`,
                    strokeDashoffset: `${2 * Math.PI * 48 * (1 - f1Score)}`,
                  }}
                />
              </svg>
              <div className="gauge__value-text">{f1Score.toFixed(2)}</div>
            </div>
            <div>
              <div className="metric-card__label">F1-Score</div>
              <div className="metric-card__hint metric-card__hint--mono">0.00 — 1.00</div>
            </div>
          </div>

          <div className="metric-card metric-card--time">
            <div className="metric-card__label">Last Updated</div>
            <div className="metric-card__big-value metric-card__big-value--small">{currentTime}</div>
            <div className="metric-card__hint metric-card__hint--success">Auto-refresh in 2s</div>
          </div>
        </motion.div>

        {activeNav === 'dashboard' && (
          <div className="dashboard-grid">
            <section className="dashboard-column dashboard-column--left">
              <article className="panel panel--feature">
                <div className="panel__header">
                  <div>
                    <div className="panel__eyebrow">Drift Radar</div>
                    <h2 className="panel__title">Feature Stability</h2>
                    <p className="panel__subtitle">Threshold PSI ≥ 0.20</p>
                  </div>
                  <div className="panel__chip">Live drift scan</div>
                </div>

                {dashboardRecentFeatures.length > 0 && (
                  <div className="feature-tags">
                    {dashboardRecentFeatures.map((feature) => (
                      <span key={feature} className="feature-tags__item">
                        {feature}
                      </span>
                    ))}
                  </div>
                )}

                <DriftChart driftData={dashboardDriftData} />
              </article>

              <article className="panel panel--feature">
                <div className="panel__header panel__header--tight">
                  <div>
                    <div className="panel__eyebrow">Performance Over Time</div>
                    <h2 className="panel__title">Self-Healing in Action</h2>
                  </div>
                  <div className="panel__chip panel__chip--muted">F1-Score</div>
                </div>
                <PerformanceChart history={dashboardHistory} />
              </article>
            </section>

            <section className="dashboard-column dashboard-column--middle">
              <article className="panel panel--registry">
                <div className="panel__header">
                  <div>
                    <div className="panel__eyebrow">Model Registry</div>
                    <h2 className="panel__title">History</h2>
                  </div>
                  <button type="button" className="panel__link" onClick={() => setActiveNav('models')}>
                    View Full Registry <ChevronRight className="h-3 w-3" />
                  </button>
                </div>

                <div className="registry-table">
                  <table>
                    <thead>
                      <tr>
                        <th>Version</th>
                        <th>Promoted At</th>
                        <th>F1-Score</th>
                        <th>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dashboardModels.map((model, index) => {
                        return (
                          <tr key={model.version}>
                            <td>
                              <div className="registry-table__version">
                                {model.is_active && <span className="registry-table__pulse" />}
                                <strong>v{model.version}</strong>
                                {model.is_active && <span className="registry-table__badge">ACTIVE</span>}
                              </div>
                            </td>
                            <td>{formatClock(model.trained_at)}</td>
                            <td className="registry-table__score">{model.f1_score.toFixed(2)}</td>
                            <td>
                              <span className="registry-table__action">
                                {index === dashboardModels.length - 1 ? 'INITIAL MODEL' : 'PROMOTED'}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </article>

              <article className="panel panel--snapshot">
                <div className="panel__header">
                  <div>
                    <div className="panel__eyebrow">Operational Snapshot</div>
                    <h2 className="panel__title">Pipeline Pulse</h2>
                  </div>
                  <div className="panel__chip panel__chip--muted">Live state</div>
                </div>

                <div className="snapshot-grid">
                  <div className="snapshot-card">
                    <span className="snapshot-card__label">State</span>
                    <strong className="snapshot-card__value snapshot-card__value--success">
                      {status.running ? 'RUNNING' : 'STOPPED'}
                    </strong>
                  </div>
                  <div className="snapshot-card">
                    <span className="snapshot-card__label">Drifted</span>
                    <strong className="snapshot-card__value">{driftCount}</strong>
                  </div>
                  <div className="snapshot-card">
                    <span className="snapshot-card__label">Models</span>
                    <strong className="snapshot-card__value">{dashboardModels.length}</strong>
                  </div>
                  <div className="snapshot-card">
                    <span className="snapshot-card__label">Events</span>
                    <strong className="snapshot-card__value">{dashboardHistory.length}</strong>
                  </div>
                </div>

                <div className="snapshot-feed">
                  <div className="snapshot-feed__row">
                    <span>Last action</span>
                    <strong>{formatActionLabel(latestEvent?.action ?? 'none')}</strong>
                  </div>
                  <div className="snapshot-feed__row">
                    <span>Latest reason</span>
                    <strong>{latestEvent?.reason ?? 'Pipeline waiting for events'}</strong>
                  </div>
                  <div className="snapshot-feed__row">
                    <span>Selected scenario</span>
                    <strong>{selectedScenario.replace('_', ' ')}</strong>
                  </div>
                </div>
              </article>
            </section>

            <section className="dashboard-column dashboard-column--right">
              <article className="panel panel--control">
                <div className="panel__header">
                  <div>
                    <div className="panel__eyebrow">Control Panel</div>
                    <h2 className="panel__title">Mission Execution</h2>
                  </div>
                  <div className="panel__chip panel__chip--muted">{status.running ? 'Live' : 'Idle'}</div>
                </div>

                <div className="stacked-field">
                  <label className="stacked-field__label">1. Adapter Selector</label>
                  <select
                    value={selectedAdapter}
                    onChange={(event) => setSelectedAdapter(event.target.value)}
                    className="dashboard-select"
                  >
                    <option value="paysim">PaySim (Production)</option>
                    <option value="fraud">Fraud Detection</option>
                    <option value="churn">Churn Prediction</option>
                  </select>
                </div>

                <div className="stacked-field">
                  <label className="stacked-field__label">2. Scenario Selector</label>
                  <div className="scenario-grid">
                    {scenarioCards.map(({ id, icon: Icon, label }) => (
                      <button
                        key={id}
                        type="button"
                        onClick={() => {
                          setSelectedScenario(id);
                          startPipeline(id);
                        }}
                        className={`scenario-card ${selectedScenario === id ? 'scenario-card--active' : ''}`}
                      >
                        <Icon className="scenario-card__icon" />
                        <span>{label}</span>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="stacked-field">
                  <label className="stacked-field__label">3. Pipeline Control</label>
                  {status.running ? (
                    <button type="button" onClick={() => stopPipeline()} className="pipeline-button pipeline-button--danger">
                      <Square className="h-5 w-5" />
                      Stop Pipeline
                    </button>
                  ) : (
                    <button type="button" onClick={() => startPipeline(selectedScenario)} className="pipeline-button pipeline-button--success">
                      <Play className="h-5 w-5" />
                      Start Pipeline
                    </button>
                  )}
                  <div className="stacked-field__hint">{status.running ? 'Pipeline is running' : 'Pipeline is stopped'}</div>
                </div>

                <div className="status-pill-row">
                  <span className="status-pill">
                    <span className={`status-pill__dot ${health.dot}`} />
                    {health.label}
                  </span>
                  <span className="status-pill status-pill--muted">Adapter: {selectedAdapter}</span>
                </div>
              </article>

              <article className="panel panel--snapshot">
                <div className="panel__header">
                  <div>
                    <div className="panel__eyebrow">Prometheus</div>
                    <h2 className="panel__title">Metrics Feed</h2>
                  </div>
                  <div className="panel__chip panel__chip--muted">/metrics/json</div>
                </div>

                <div className="snapshot-grid">
                  <div className="snapshot-card">
                    <span className="snapshot-card__label">Families</span>
                    <strong className="snapshot-card__value">{metricsFamilyCount}</strong>
                  </div>
                  <div className="snapshot-card">
                    <span className="snapshot-card__label">Samples</span>
                    <strong className="snapshot-card__value">{metricsSampleCount}</strong>
                  </div>
                  <div className="snapshot-card">
                    <span className="snapshot-card__label">Requests</span>
                    <strong className="snapshot-card__value">{requestCount.toLocaleString()}</strong>
                  </div>
                  <div className="snapshot-card">
                    <span className="snapshot-card__label">Avg Latency</span>
                    <strong className="snapshot-card__value snapshot-card__value--success">
                      {formatLatency(averageLatencyMs === null ? null : averageLatencyMs / 1000)}
                    </strong>
                  </div>
                </div>

                <div className="snapshot-feed">
                  <div className="snapshot-feed__row">
                    <span>Primary metric</span>
                    <strong>{latencyFamily?.help ?? 'API request latency in seconds'}</strong>
                  </div>
                  <div className="snapshot-feed__row">
                    <span>Backend scrape</span>
                    <strong>{latencyFamily ? 'Live from FastAPI registry' : 'Waiting for metrics'}</strong>
                  </div>
                  <div className="snapshot-feed__row">
                    <span>Endpoint</span>
                    <strong>GET /metrics/json</strong>
                  </div>
                </div>
              </article>

              {status.shadow_model_version ? <ShadowArena status={status} /> : null}

              <article className="panel panel--explainable">
                <div className="panel__header">
                  <div>
                    <div className="panel__eyebrow">Explainable AI</div>
                    <h2 className="panel__title">Top Feature Weights</h2>
                  </div>
                  <Sparkles className="h-4 w-4 text-amber-400" />
                </div>

                <div className="explainable-box">
                  {Object.keys(importanceData).length > 0 ? (
                    <ImportanceChart importance={importanceData} />
                  ) : (
                    <div className="explainable-box__empty">No weights available</div>
                  )}
                </div>
              </article>

              <article className="panel panel--events">
                <div className="panel__header">
                  <div>
                    <div className="panel__eyebrow">System Events</div>
                    <h2 className="panel__title">Latest Activity</h2>
                  </div>
                  <button type="button" className="panel__link" onClick={() => setActiveNav('logs')}>
                    View All <ChevronRight className="h-3 w-3" />
                  </button>
                </div>

                <div className="event-list">
                  {dashboardHistory.map((entry, index) => (
                    <div key={`${entry.iteration}-${index}`} className="event-card">
                      <div className="event-card__icon">
                        {entry.action === 'promote' ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                        ) : entry.action === 'retrain' || entry.action === 'shadow' ? (
                          <RefreshCw className="h-4 w-4 text-amber-400" />
                        ) : (
                          <Activity className="h-4 w-4 text-slate-400" />
                        )}
                      </div>

                      <div className="event-card__body">
                        <div className="event-card__header">
                          <strong>{formatActionLabel(entry.action)}</strong>
                          <span>{formatClock(entry.timestamp)}</span>
                        </div>
                        <p>{entry.reason}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </article>
            </section>
          </div>
        )}

        {activeNav === 'drift' && (
          <div className="dashboard-view-grid">
            <article className="panel panel--feature">
              <div className="panel__header">
                <div>
                  <div className="panel__eyebrow">Drift Radar</div>
                  <h2 className="panel__title">Focused Stability View</h2>
                  <p className="panel__subtitle">Current PSI trend and affected features.</p>
                </div>
                <div className="panel__chip">Live scan</div>
              </div>
              <DriftChart driftData={driftData} />
            </article>

            <article className="panel panel--snapshot">
              <div className="panel__header">
                <div>
                  <div className="panel__eyebrow">Current Drift Summary</div>
                  <h2 className="panel__title">High-Signal Features</h2>
                </div>
                <div className="panel__chip panel__chip--muted">{driftCount} features</div>
              </div>
              <div className="feature-tags feature-tags--large">
                {Object.entries(driftData).map(([feature]) => (
                  <span key={feature} className="feature-tags__item feature-tags__item--wide">
                    {feature}
                  </span>
                ))}
              </div>
              <div className="snapshot-feed">
                {driftedHistory.length > 0 ? driftedHistory.map((entry) => (
                  <div key={`${entry.iteration}-${entry.timestamp}`} className="snapshot-feed__row">
                    <span>Iteration {entry.iteration}</span>
                    <strong>{formatActionLabel(entry.action)} · PSI {entry.drift_score.toFixed(2)}</strong>
                  </div>
                )) : (
                  <div className="explainable-box__empty">No recent drift events</div>
                )}
              </div>
            </article>
          </div>
        )}

        {activeNav === 'models' && (
          <div className="dashboard-view-grid">
            <article className="panel panel--registry panel--registry-full">
              <div className="panel__header">
                <div>
                  <div className="panel__eyebrow">Model Registry</div>
                  <h2 className="panel__title">Version History</h2>
                </div>
                <div className="panel__chip panel__chip--muted">{sortedModels.length} visible</div>
              </div>
              <div className="registry-table">
                <table>
                  <thead>
                    <tr>
                      <th>Version</th>
                      <th>Promoted At</th>
                      <th>F1-Score</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedModels.map((model, index) => (
                      <tr key={model.version}>
                        <td>
                          <div className="registry-table__version">
                            {model.is_active && <span className="registry-table__pulse" />}
                            <strong>v{model.version}</strong>
                            {model.is_active && <span className="registry-table__badge">ACTIVE</span>}
                          </div>
                        </td>
                        <td>{formatClock(model.trained_at)}</td>
                        <td className="registry-table__score">{model.f1_score.toFixed(2)}</td>
                        <td>
                          <span className="registry-table__action">
                            {index === sortedModels.length - 1 ? 'INITIAL MODEL' : 'PROMOTED'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </article>
          </div>
        )}

        {activeNav === 'performance' && (
          <div className="dashboard-view-grid">
            <article className="panel panel--feature panel--feature-full">
              <div className="panel__header">
                <div>
                  <div className="panel__eyebrow">Performance</div>
                  <h2 className="panel__title">Self-Healing in Action</h2>
                </div>
                <div className="panel__chip panel__chip--muted">F1-Score</div>
              </div>
              <PerformanceChart history={history} />
            </article>
          </div>
        )}

        {activeNav === 'alerts' && (
          <div className="dashboard-view-grid">
            <article className="panel panel--feature">
              <div className="panel__header">
                <div>
                  <div className="panel__eyebrow">Alerts</div>
                  <h2 className="panel__title">Warning Feed</h2>
                  <p className="panel__subtitle">Only non-normal actions are shown here.</p>
                </div>
                <div className="panel__chip panel__chip--muted">{alertHistory.length} items</div>
              </div>
              <div className="event-list">
                {alertHistory.length > 0 ? alertHistory.map((entry, index) => (
                  <div key={`${entry.iteration}-${index}`} className="event-card">
                    <div className="event-card__icon">
                      {entry.action === 'promote' ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                      ) : entry.action === 'retrain' || entry.action === 'shadow' ? (
                        <RefreshCw className="h-4 w-4 text-amber-400" />
                      ) : (
                        <Activity className="h-4 w-4 text-rose-400" />
                      )}
                    </div>
                    <div className="event-card__body">
                      <div className="event-card__header">
                        <strong>{formatActionLabel(entry.action)}</strong>
                        <span>{formatClock(entry.timestamp)}</span>
                      </div>
                      <p>{entry.reason}</p>
                    </div>
                  </div>
                )) : (
                  <div className="explainable-box__empty">No active alerts. Pipeline is stable.</div>
                )}
              </div>
            </article>

            <article className="panel panel--snapshot">
              <div className="panel__header">
                <div>
                  <div className="panel__eyebrow">Health</div>
                  <h2 className="panel__title">Current State</h2>
                </div>
                <div className="panel__chip">{health.label}</div>
              </div>
              <div className="snapshot-grid">
                <div className="snapshot-card">
                  <span className="snapshot-card__label">Running</span>
                  <strong className="snapshot-card__value snapshot-card__value--success">{status.running ? 'YES' : 'NO'}</strong>
                </div>
                <div className="snapshot-card">
                  <span className="snapshot-card__label">Drifted</span>
                  <strong className="snapshot-card__value">{driftCount}</strong>
                </div>
                <div className="snapshot-card">
                  <span className="snapshot-card__label">F1</span>
                  <strong className="snapshot-card__value">{f1Score.toFixed(2)}</strong>
                </div>
                <div className="snapshot-card">
                  <span className="snapshot-card__label">Action</span>
                  <strong className="snapshot-card__value">{formatActionLabel(status.last_action)}</strong>
                </div>
              </div>
            </article>
          </div>
        )}

        {activeNav === 'logs' && (
          <div className="dashboard-view-grid">
            <article className="panel panel--events panel--events-full">
              <div className="panel__header">
                <div>
                  <div className="panel__eyebrow">Logs</div>
                  <h2 className="panel__title">Recent Activity</h2>
                </div>
                <div className="panel__chip panel__chip--muted">{aggregatedHistory.length} events</div>
              </div>
              <div className="event-list">
                {aggregatedHistory.map((entry, index) => (
                  <div key={`${entry.iteration}-${index}`} className={`event-card ${entry.isAggregated ? 'event-card--aggregated' : ''}`}>
                    <div className="event-card__icon">
                      {entry.action === 'promote' ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                      ) : entry.action === 'retrain' || entry.action === 'shadow' ? (
                        <RefreshCw className="h-4 w-4 text-amber-400" />
                      ) : entry.action === 'stable' ? (
                        <ShieldCheck className="h-4 w-4 text-emerald-300" />
                      ) : (
                        <Activity className="h-4 w-4 text-slate-400" />
                      )}
                    </div>
                    <div className="event-card__body">
                      <div className="event-card__header">
                        <strong>{entry.action === 'stable' ? '✓ stable' : formatActionLabel(entry.action)}</strong>
                        <span>{formatClock(entry.timestamp)}</span>
                      </div>
                      <p>{entry.reason}</p>
                      {entry.isAggregated && (
                        <div className="event-card__meta">
                          Iterations {entry.iteration - entry.stableIterations! + 1}–{entry.iteration}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </article>

            <article className="panel panel--snapshot">
              <div className="panel__header">
                <div>
                  <div className="panel__eyebrow">System Snapshot</div>
                  <h2 className="panel__title">Runtime Context</h2>
                </div>
                <div className="panel__chip panel__chip--muted">{currentTime}</div>
              </div>
              <div className="snapshot-feed">
                <div className="snapshot-feed__row">
                  <span>Active model</span>
                  <strong>{activeModel ? `v${activeModel.version}` : 'none'}</strong>
                </div>
                <div className="snapshot-feed__row">
                  <span>Scenario</span>
                  <strong>{selectedScenario.replace('_', ' ')}</strong>
                </div>
                <div className="snapshot-feed__row">
                  <span>Adapter</span>
                  <strong>{selectedAdapter}</strong>
                </div>
              </div>
            </article>
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
