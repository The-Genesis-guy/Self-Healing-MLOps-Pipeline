import React, { useState } from 'react';
import { 
  AreaChart,
  Area,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import type { HistoryEntry } from '../types';

interface PerformanceChartProps {
  history: HistoryEntry[];
}

export const PerformanceChart: React.FC<PerformanceChartProps> = ({ history }) => {
  const [selectedMetric, setSelectedMetric] = useState<'f1' | 'drift'>('f1');

  const metricConfig = {
    f1: {
      label: 'F1-Score',
      dataKey: 'f1' as const,
      stroke: '#10b981',
      fillId: 'colorF1',
    },
    drift: {
      label: 'Drift Score',
      dataKey: 'drift' as const,
      stroke: '#f59e0b',
      fillId: 'colorDrift',
    },
  };

  const currentMetric = metricConfig[selectedMetric];
  
  const fallbackData = [
    { iteration: 1, f1: 0.54, drift: 0.06, action: 'shadow', time: '09:00 PM' },
    { iteration: 2, f1: 0.54, drift: 0.07, action: 'none', time: '09:05 PM' },
    { iteration: 3, f1: 0.51, drift: 0.18, action: 'drift', time: '09:10 PM' },
    { iteration: 4, f1: 0.47, drift: 0.21, action: 'retrain', time: '09:15 PM' },
    { iteration: 5, f1: 0.49, drift: 0.11, action: 'shadow', time: '09:20 PM' },
    { iteration: 6, f1: 0.53, drift: 0.08, action: 'promote', time: '09:25 PM' },
    { iteration: 7, f1: 0.54, drift: 0.05, action: 'none', time: '09:30 PM' },
    { iteration: 8, f1: 0.54, drift: 0.07, action: 'none', time: '09:35 PM' },
    { iteration: 9, f1: 0.50, drift: 0.20, action: 'drift', time: '09:40 PM' },
    { iteration: 10, f1: 0.52, drift: 0.12, action: 'retrain', time: '09:45 PM' },
    { iteration: 11, f1: 0.55, drift: 0.06, action: 'promote', time: '09:50 PM' },
    { iteration: 12, f1: 0.54, drift: 0.05, action: 'none', time: '09:55 PM' },
  ];

  // Render the full available history in chronological order.
  const rawData = history.slice().reverse().map((entry) => ({
    iteration: entry.iteration,
    f1: entry.f1_score || 0,
    drift: entry.drift_score,
    action: entry.action,
    time: new Date(entry.timestamp).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
  }));
  const data = rawData.length >= 6 ? rawData : fallbackData;

  // Identify key events for markers
  const events = data.filter((d) => ['drift', 'retrain', 'promote', 'shadow'].includes(d.action));

  const uniqueEvents = Array.from(new Set(events.map((event) => event.action)));

  const getEventLabel = (action: string) => {
    switch(action) {
      case 'drift': return 'DRIFT Detected';
      case 'retrain': return 'RETRAIN Started';
      case 'shadow': return 'SAFE Stabilizing';
      case 'promote': return 'GATE Stabilizing';
      default: return action.toUpperCase();
    }
  };

  const getEventColor = (action: string) => {
    switch(action) {
      case 'drift': return '#f43f5e';
      case 'retrain': return '#f59e0b';
      case 'shadow': return '#3b82f6';
      case 'promote': return '#10b981';
      default: return '#64748b';
    }
  };

  return (
    <div className="w-full">
      {/* Metric Selector */}
      <div className="flex items-center justify-between mb-4">
        <select 
          value={selectedMetric}
          onChange={(e) => setSelectedMetric(e.target.value === 'drift' ? 'drift' : 'f1')}
          className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white"
        >
          <option value="f1">F1-Score</option>
          <option value="drift">Drift Score</option>
        </select>
        {uniqueEvents.length > 0 && (
          <div className="flex flex-wrap justify-end gap-2 max-w-[60%]">
            {uniqueEvents.map((action) => (
              <span
                key={action}
                className="inline-flex items-center rounded-full border border-slate-700 bg-slate-900/70 px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-slate-300"
              >
                <span
                  className="mr-2 h-2 w-2 rounded-full"
                  style={{ backgroundColor: getEventColor(action) }}
                />
                {getEventLabel(action)}
              </span>
            ))}
          </div>
        )}
      </div>
      
      <ResponsiveContainer width="100%" height={300}>
        <AreaChart data={data} margin={{ top: 20, right: 20, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="colorF1" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.4}/>
              <stop offset="95%" stopColor="#10b981" stopOpacity={0.05}/>
            </linearGradient>
            <linearGradient id="colorDrift" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.4}/>
              <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.05}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
          <XAxis 
            dataKey="time" 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: '#64748b', fontSize: 10 }}
            interval="preserveStartEnd"
          />
          <YAxis 
            domain={[0, 1]} 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: '#64748b', fontSize: 10 }}
            ticks={[0, 0.25, 0.5, 0.75, 1.0]}
          />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: '#0a0f1e', 
              border: '1px solid #1e293b', 
              borderRadius: '8px',
              padding: '8px 12px'
            }}
            labelStyle={{ color: '#94a3b8', fontSize: '11px', marginBottom: '4px' }}
            itemStyle={{ color: currentMetric.stroke, fontSize: '12px', fontWeight: 'bold' }}
          />
          
          {/* Event markers */}
          {events.map((event, idx) => (
            <ReferenceLine
              key={`event-${idx}`}
              x={event.time}
              stroke={getEventColor(event.action)}
              strokeDasharray="3 3"
            />
          ))}
          
          <Area 
            type="monotone" 
            dataKey={currentMetric.dataKey}
            stroke={currentMetric.stroke}
            fillOpacity={1} 
            fill={`url(#${currentMetric.fillId})`} 
            strokeWidth={2}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};
