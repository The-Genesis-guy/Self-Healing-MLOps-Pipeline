# LAYER 1: Frontend Dashboard Documentation

**React 19 + TypeScript + Vite + Recharts**

This document details the complete frontend architecture, component structure, styling system, data binding, and real-time update mechanisms of the GUARDIAN dashboard.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Tech Stack](#tech-stack)
3. [Project Structure](#project-structure)
4. [Component Hierarchy](#component-hierarchy)
5. [Page Descriptions](#page-descriptions)
6. [Data Binding & State Management](#data-binding--state-management)
7. [Styling System](#styling-system)
8. [Charts & Visualizations](#charts--visualizations)
9. [Real-Time Updates](#real-time-updates)
10. [Log Aggregation Algorithm](#log-aggregation-algorithm)
11. [Performance Optimization](#performance-optimization)
12. [Development Guide](#development-guide)

---

## Architecture Overview

The frontend is a **single-page application (SPA)** built with React 19 that communicates with the FastAPI backend via REST APIs. The dashboard provides real-time visibility into the pipeline with auto-refreshing metrics every 2 seconds.

### Design Principles

- **Unidirectional Data Flow**: Data fetched from API → Component state → UI render
- **Separation of Concerns**: Components are focused, reusable, and testable
- **Real-Time Updates**: 2-second polling interval for live metrics
- **Type Safety**: Full TypeScript coverage with Pydantic-generated interfaces
- **Performance**: Optimized rendering with React hooks and memoization
- **Accessibility**: Semantic HTML, proper color contrast, ARIA labels

---

## Tech Stack

| Technology | Purpose | Version |
|------------|---------|---------|
| React | UI framework | 19 |
| TypeScript | Type safety & dev experience | 5.x |
| Vite | Build tool & dev server | 8.x |
| Recharts | Chart library | Latest |
| Framer Motion | Animation library | Latest |
| Lucide Icons | Icon system | Latest |
| Tailwind CSS | Utility classes (custom) | CSS Grid/Flexbox |

### Build Configuration

- **Mode**: Development (vite dev) or Production (vite build)
- **Output**: `dist/` folder with `index.html`, CSS, and JS bundles
- **Minification**: Enabled in production
- **Chunk Size**: ~760KB minified (single bundle)

---

## Project Structure

```
dashboard/
├── src/
│   ├── App.tsx                 # Main component (page router)
│   ├── App.css                 # Global styling
│   ├── main.tsx                # Entry point
│   ├── index.css               # Base styles
│   ├── types.ts                # TypeScript interfaces
│   ├── usePipeline.ts          # Custom hook for API calls
│   ├── components/             # Reusable components
│   │   ├── DriftChart.tsx      # Feature drift visualization
│   │   ├── PerformanceChart.tsx # F1-Score & Drift trends
│   │   ├── ImportanceChart.tsx # Feature importance bars
│   │   └── ShadowArena.tsx     # Shadow trial status
│   └── assets/                 # Static images & icons
├── dist/                       # Build output
├── public/                     # Public assets (favicon, etc.)
├── package.json                # Dependencies
├── tsconfig.json               # TypeScript config
├── tsconfig.app.json           # App-specific TS config
├── vite.config.ts              # Vite configuration
└── index.html                  # HTML template

Key Files:
- App.tsx: 900+ lines, all pages & logic
- App.css: 900+ lines, all styling
- usePipeline.ts: API polling & data management
- types.ts: Interface definitions
```

---

## Component Hierarchy

### Main App Component Structure

```
<App>                          # Main router & page controller
├── Sidebar
│   ├── Brand logo
│   ├── Navigation buttons (6 pages)
│   ├── Configuration buttons
│   └── System stats
└── Main Content Area
    ├── Page Header (title, description, health status)
    ├── Metrics Strip (iteration, F1, status, etc.)
    └── Page-Specific Content
        ├── Dashboard Page
        │   ├── Drift Chart section
        │   ├── Performance Chart section
        │   ├── Model Registry table
        │   ├── Operational Snapshot
        │   ├── Control Panel
        │   ├── Shadow Arena (if active)
        │   ├── Feature Importance chart
        │   └── System Events
        │
        ├── Drift Radar Page
        │   ├── Drift Chart (full view)
        │   └── Drift Summary with feature tags
        │
        ├── Model Registry Page
        │   └── Full model table (sorted by version DESC)
        │
        ├── Performance Page
        │   ├── Metric selector dropdown
        │   └── Performance Chart (full height)
        │
        ├── Alerts Page
        │   ├── Warning feed (non-normal actions)
        │   └── Health snapshot
        │
        └── Logs Page
            ├── Aggregated event timeline
            └── System runtime context
```

### Component Implementation Details

#### DriftChart Component
- **Props**: `driftData: { [feature: string]: psiScore }`
- **Renders**: Radar/Scatter plot with PSI scores
- **Features**:
  - Color-coded by severity (green/yellow/orange/red)
  - Interactive hover tooltips
  - Legend showing thresholds (0.10, 0.20, 0.30)
  - Responsive sizing

#### PerformanceChart Component
- **Props**: `history: HistoryEntry[], metric: 'f1' | 'drift'`
- **Renders**: Line chart with event markers
- **Features**:
  - F1-Score and Drift Score traces
  - Event markers for major actions (retrain, promote, rollback, shadow)
  - Toggleable metric selector
  - Time-series with iteration numbers on X-axis
  - Legend with symbol indicators

#### ImportanceChart Component
- **Props**: `importance: { [feature: string]: score }`
- **Renders**: Horizontal bar chart of feature weights
- **Features**:
  - Top N features sorted by importance
  - Gradient coloring (blue → green)
  - Percentage labels on bars
  - Responsive layout

#### ShadowArena Component
- **Props**: `status: PipelineStatus`
- **Renders**: Shadow trial progress card
- **Features**:
  - Active vs. Shadow model comparison
  - F1-Score comparison gauge
  - Status indicator (In Trial, Promoting, etc.)
  - Expected promotion time estimate

---

## Page Descriptions

### Page 1: Dashboard (Home)

**Purpose**: Executive overview with key metrics and actionable insights

**Sections**:
1. **Metrics Strip**
   - Pipeline Status (RUNNING/STOPPED with indicator)
   - Current Iteration counter
   - Active Model version
   - F1-Score gauge (circular progress)
   - Last Updated timestamp

2. **Left Column**
   - Drift Radar (top 6 features)
   - Performance Chart (last 5 events)

3. **Middle Column**
   - Model Registry (last 5 versions)
   - Operational Snapshot (state, drifts, models, events)

4. **Right Column**
   - Control Panel (adapter, scenario, start/stop)
   - Shadow Arena (if model in trial)
   - Feature Importance chart
   - System Events (last 5 actions)

**Update Interval**: 2 seconds (auto-refresh)

### Page 2: Drift Radar

**Purpose**: Focused analysis of feature drift and stability

**Content**:
- Full drift chart (all features)
- Feature stability table with:
  - Rank number
  - Feature name
  - PSI score
  - Status badge (NORMAL/MILD/HIGH/SEVERE)
  - Trend arrow (↑↓→)
- Current drift summary
- Recent drift events

**Update Interval**: 2 seconds

### Page 3: Model Registry

**Purpose**: Complete version history and promotion lineage

**Table Columns**:
- Version (with "ACTIVE" badge)
- Promoted At (timestamp)
- F1-Score (2 decimal places)
- Action (INITIAL MODEL / PROMOTED)

**Features**:
- Sortable by version (descending)
- Hover state showing full timestamp
- Active model highlighted with pulse indicator
- Scrollable for 13+ versions

**Update Interval**: 2 seconds

### Page 4: Performance

**Purpose**: Trend analysis of F1-Score evolution and retraining points

**Content**:
- **Metric Selector Dropdown**: Switch between F1-Score and Drift Score
- **Performance Chart**: 
  - Line plot of selected metric over iterations
  - Event markers for: retrain, promote, shadow, rollback, alert
  - Legend showing event types
  - Interactive data points on hover

**Analysis Features**:
- Identify retraining effectiveness
- See shadow trial success/failure
- Track metric improvements after healing

**Update Interval**: 2 seconds

### Page 5: Alerts

**Purpose**: Warning dashboard for non-stable events

**Content**:
- **Warning Feed**: All events where action ≠ "none"
  - Retrain actions
  - Rollback actions
  - Safe mode alerts
  - Failed retrain events
- **Health Snapshot**:
  - Running status
  - Drifted features count
  - F1-Score current value
  - Last action taken

**Message**: "No active alerts. Pipeline is stable." (when action == "none")

**Update Interval**: 2 seconds

### Page 6: Logs

**Purpose**: Complete event history with intelligent aggregation

**Features**:
- **Log Aggregation**:
  - Groups 3+ consecutive "none" actions into single entry
  - Shows: "✓ stable — Pipeline stable for X iterations (Ym)"
  - Green styling for stability indication
  - Iteration range shown (e.g., "Iterations 897–996")

- **Individual Entries**: For non-"none" actions (retrain, alert, etc.)

- **System Snapshot**:
  - Active model version
  - Current scenario
  - Current adapter

**Event Card Format**:
```
[Icon] [Action Label] [Timestamp]
       [Reason text]
       [Metadata if aggregated]
```

**Update Interval**: 2 seconds

---

## Data Binding & State Management

### usePipeline Hook

**Location**: `src/usePipeline.ts`

**Responsibilities**:
1. Fetch data from all API endpoints
2. Maintain local state with `useState`
3. Poll backend every 2 seconds with `setInterval`
4. Handle loading states and errors
5. Return data to components

**Fetched Data**:
```typescript
interface UsePipelineReturn {
  status: PipelineStatus | null;      // /pipeline/status
  history: HistoryEntry[];             // /pipeline/history
  models: ModelResponse[];              // /models
  driftReports: DriftReportResponse;    // /pipeline/drift
  loading: boolean;
  startPipeline: (scenario: string) => void;
  stopPipeline: () => void;
}
```

**API Endpoints**:
- `GET /pipeline/status` - Current state
- `GET /pipeline/history?limit=100` - Event log
- `GET /models` - Model registry
- `GET /pipeline/drift` - Feature drift

**Polling Mechanism**:
```typescript
useEffect(() => {
  const interval = setInterval(async () => {
    const [status, history, models, drift] = await Promise.all([
      fetch('/pipeline/status'),
      fetch('/pipeline/history'),
      fetch('/models'),
      fetch('/pipeline/drift')
    ]);
    // Update state
  }, 2000);
  
  return () => clearInterval(interval);
}, []);
```

### State Flow in App.tsx

```
┌─────────────────────────────────────┐
│     usePipeline Hook                │
│  Fetches API data every 2 seconds    │
└────────────────┬────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│     App Component State              │
│  selectedAdapter, selectedScenario   │
│  activeNav (current page)            │
└────────────────┬────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│     Derived State                   │
│  dashboardHistory, dashboardModels  │
│  aggregatedHistory, alertHistory    │
└────────────────┬────────────────────┘
                 ↓
┌─────────────────────────────────────┐
│     Page Components                 │
│  Receive data via props              │
│  Render content                      │
└─────────────────────────────────────┘
```

---

## Styling System

### Design System

**Color Palette**:
```css
/* Primary Colors */
--primary: #10b981    /* Emerald - Success */
--warning: #fbbf24    /* Amber - Warning */
--danger: #ef4444     /* Red - Error */
--info: #3b82f6       /* Blue - Info */

/* Neutrals */
--bg-dark: #040914    /* Very dark background */
--bg-card: #0f172a    /* Card background */
--text-primary: #f1f5f9   /* Primary text */
--text-secondary: #cbd5e1 /* Secondary text */
--border: #334155     /* Border color */
```

**Typography**:
- **Headings**: 600-800 font weight, 1.2-1.5 line height
- **Body**: 400 font weight, 1.4-1.6 line height
- **Labels**: 500 font weight, 0.7-0.8rem size

**Spacing**:
- Base unit: 0.25rem (4px)
- Common: 0.5rem, 1rem, 1.5rem, 2rem, 3rem

**Border Radius**:
- Small: 0.5rem
- Medium: 1rem
- Large: 1.5rem
- Pill: 999px

### CSS Organization

**App.css Structure**:

1. **Reset & Base** (lines 1-100)
   - Browser reset
   - Base element styling
   - Utility classes

2. **Layout Components** (lines 100-300)
   - `.app-shell` - Main layout
   - `.app-sidebar` - Left navigation
   - `.app-main` - Content area
   - `.dashboard-grid` - Page grid

3. **Navigation & Sidebar** (lines 300-450)
   - `.sidebar-brand`
   - `.sidebar-nav`
   - `.sidebar-group`
   - `.stat-row`

4. **Cards & Panels** (lines 450-600)
   - `.panel`
   - `.metric-card`
   - `.snapshot-card`
   - `.event-card`

5. **Charts & Tables** (lines 600-750)
   - `.gauge`
   - `.registry-table`
   - `.drift-table`
   - `.event-list`

6. **Controls & Forms** (lines 750-850)
   - `.dashboard-select`
   - `.scenario-card`
   - `.pipeline-button`
   - `.stacked-field`

7. **Responsive & Media Queries** (lines 850-900)
   - Breakpoints: 1440px, 1200px, 768px

### Key CSS Classes

```css
/* Containers */
.app-shell { display: flex; overflow: hidden; }
.dashboard-grid { display: grid; grid-template-columns: ... }
.panel { border: 1px solid rgba(51, 65, 85, 0.7); ... }

/* Text & Typography */
.dashboard-hero__title { font-size: 2rem; font-weight: 700; }
.panel__subtitle { font-size: 0.75rem; color: rgba(148, 163, 184, 0.78); }

/* Color Variants */
.metric-card__value--live { color: #34d399; }
.metric-card__value--idle { color: #64748b; }
.status-pill--danger { background: rgba(239, 68, 68, 0.1); }

/* Interactive */
.event-card--aggregated { border-color: rgba(34, 197, 94, 0.3); }
.event-card--aggregated .event-card__header strong { color: #34d399; }
```

---

## Charts & Visualizations

### DriftChart (Radar Plot)

**Data Mapping**:
```typescript
// Input: { feature: string, psi: number }[]
// Renders as circular radar with PSI values on radius

Configuration:
- angleAxisType: 'category' (features on outer ring)
- polarRadiusAxis: (0 to max PSI)
- seriesType: 'scatter' or 'line'
- color gradient: green → yellow → orange → red (by PSI)
```

**PSI Color Coding**:
- 0.00-0.10: Green (#34d399)
- 0.10-0.20: Amber (#fbbf24)
- 0.20-0.30: Orange (#f97316)
- 0.30+: Red (#ef4444)

### PerformanceChart (Line + Scatter)

**Data Mapping**:
```typescript
// Input: HistoryEntry[] (sorted by iteration DESC)
// X-axis: Iteration number
// Y-axis: F1-Score or Drift Score (selectable)
// Points: Event markers (retrain, promote, shadow, alert)
```

**Event Markers**:
```
Color: Based on action type
  - Retrain: Amber (#f97316)
  - Promote: Green (#34d399)
  - Shadow: Blue (#3b82f6)
  - Alert: Red (#ef4444)
  - Rollback: Orange (#ea580c)

Shape: Circle with icon

Tooltip: Shows iteration, timestamp, action, reason
```

**Metric Selector Logic**:
```typescript
const selectedMetric = metric === 'f1' ? 'f1_score' : 'drift_score';
const dataPoints = history.map(entry => ({
  iteration: entry.iteration,
  timestamp: entry.timestamp,
  value: entry[selectedMetric],
  action: entry.action
}));
```

### ImportanceChart (Bar Chart)

**Data Mapping**:
```typescript
// Input: { feature: string, weight: number }
// Sorted by weight descending
// Bars: Horizontal layout
// Colors: Gradient from blue → green (by rank)
```

**Features**:
- Top 10 features displayed
- Percentage of total importance shown on bar
- Feature name as label
- Responsive width

---

## Real-Time Updates

### 2-Second Polling Mechanism

**Implementation**:
```typescript
useEffect(() => {
  const interval = setInterval(async () => {
    // Fetch all data in parallel
    const [statusRes, historyRes, modelsRes, driftRes] = 
      await Promise.all([
        fetch(url + '/pipeline/status'),
        fetch(url + '/pipeline/history'),
        fetch(url + '/models'),
        fetch(url + '/pipeline/drift')
      ]);
    
    // Parse JSON
    const [status, history, models, drift] = await Promise.all([
      statusRes.json(),
      historyRes.json(),
      modelsRes.json(),
      driftRes.json()
    ]);
    
    // Update state
    setState({ status, history, models, drift });
  }, 2000);
  
  return () => clearInterval(interval);
}, []);
```

**Performance Optimization**:
- Single `setInterval` instead of multiple
- `Promise.all` for parallel requests
- Conditional state updates (only update if changed)
- No re-renders on unchanged data

**Network Impact**:
- 4 API calls every 2 seconds
- ~10KB response total
- ~5KB/sec bandwidth usage
- Minimal backend load

---

## Log Aggregation Algorithm

### aggregateStablePeriods Function

**Purpose**: Compress consecutive "none" actions (3+ entries) into summary

**Algorithm**:
```typescript
function aggregateStablePeriods(history: HistoryEntry[]): AggregatedEntry[] {
  const aggregated: AggregatedEntry[] = [];
  let i = 0;
  
  while (i < history.length) {
    if (history[i].action === 'none') {
      const groupStart = i;
      
      // Find consecutive "none" entries
      while (i < history.length && history[i].action === 'none') {
        i++;
      }
      
      const groupSize = i - groupStart;
      
      // Only aggregate if 3+ entries
      if (groupSize >= 3) {
        const firstEntry = history[groupStart];
        const lastEntry = history[i - 1];
        
        // Calculate duration
        const firstTime = new Date(lastEntry.timestamp);
        const lastTime = new Date(firstEntry.timestamp);
        const durationMins = Math.round(
          (lastTime - firstTime) / 60000
        );
        
        // Format duration string
        const timeDuration = durationMins < 60 
          ? `${durationMins}m`
          : `${Math.floor(durationMins/60)}h ${durationMins%60}m`;
        
        aggregated.push({
          action: 'stable',
          reason: `Pipeline stable for ${groupSize} iterations (${timeDuration})`,
          isAggregated: true,
          stableIterations: groupSize,
          iterationRange: `${firstEntry.iteration - groupSize + 1}–${firstEntry.iteration}`
        });
      } else {
        // Add individually if < 3
        for (let j = groupStart; j < i; j++) {
          aggregated.push(history[j]);
        }
      }
    } else {
      aggregated.push(history[i]);
      i++;
    }
  }
  
  return aggregated;
}
```

**Time Complexity**: O(n) - single pass through history
**Space Complexity**: O(n) - output array

**Example**:
```
Input:  [n, n, n, n, n, retrain, n, n, n, alert]
Output: [stable (5 iters), retrain, stable (3 iters), alert]
Compression: 10 entries → 4 entries (60% reduction)
```

---

## Performance Optimization

### Rendering Optimization

1. **Component Memoization**
   - Charts wrapped with React.memo
   - Prevents unnecessary re-renders on prop equality

2. **Derived State**
   - Calculate dashboardHistory, aggregatedHistory once per render
   - Avoid inline calculations in JSX

3. **Event Delegation**
   - Navigation buttons use onClick handlers
   - Single event listener instead of multiple

4. **CSS-in-JS Avoidance**
   - All styles in App.css (no styled-components)
   - Faster stylesheet parsing

### Data Fetching Optimization

1. **Parallel Requests**
   - Use Promise.all for concurrent API calls
   - Reduce total fetch time

2. **Response Filtering**
   - Only fetch history limit=100 (not all 2,120)
   - Reduce payload size

3. **Caching Strategy**
   - Browser caches responses (Cache-Control headers)
   - Reduce redundant requests

### Bundle Size

- **Production Build**: 762KB minified (includes all dependencies)
- **Gzip Compression**: 230KB (70% reduction)
- **Vendor Split**: React + libraries in separate chunk
- **Chunk Size Warning**: Non-critical (warning only, no impact)

---

## Development Guide

### Adding a New Page

1. **Add Page Metadata**:
```typescript
const pageMeta = {
  ...
  newpage: {
    eyebrow: 'Category',
    title: 'Page Title',
    description: 'Page description'
  }
};
```

2. **Add Navigation Item**:
```typescript
const navItems = [
  ...
  { id: 'newpage', icon: IconComponent, label: 'Label' }
];
```

3. **Add Conditional Render**:
```typescript
{activeNav === 'newpage' && (
  <div className="dashboard-view-grid">
    <article className="panel">
      {/* Page content */}
    </article>
  </div>
)}
```

### Adding a New Chart

1. **Create Component**:
```typescript
// components/NewChart.tsx
export const NewChart: React.FC<{ data: any[] }> = ({ data }) => {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <ChartType data={data}>
        {/* Chart configuration */}
      </ChartType>
    </ResponsiveContainer>
  );
};
```

2. **Import & Use**:
```typescript
import { NewChart } from './components/NewChart';

// In component JSX:
<NewChart data={chartData} />
```

### Styling Best Practices

- Use existing CSS classes from App.css
- Follow BEM naming convention (`.block__element--modifier`)
- Use CSS Grid for layouts (2D)
- Use Flexbox for components (1D)
- Maintain color consistency

### Testing

Run in dev environment:
```bash
npm run dev
# View at http://localhost:5173
```

Build for production:
```bash
npm run build
# Output in dist/
```

---

## Common Issues & Solutions

### Charts Not Rendering

**Issue**: "The width(-1) and height(-1) of chart should be greater than 0"

**Cause**: ResponsiveContainer needs explicit parent height

**Solution**: Set `height: 300px` on parent div

### Data Not Updating

**Issue**: Dashboard shows stale data

**Cause**: API fetch error or interval not running

**Solution**: Check browser console for fetch errors, verify backend is running

### Styling Not Applied

**Issue**: CSS classes not taking effect

**Cause**: CSS specificity conflicts or missing import

**Solution**: Check App.css load order, increase specificity with !important if needed

---

**For general dashboard information, see [README.md](../README.md)**
