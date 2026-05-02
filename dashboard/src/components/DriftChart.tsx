import React from 'react';

interface DriftChartProps {
  driftData: Record<string, number>;
}

// Generate sparkline SVG path from PSI history
const generateSparkline = (psi: number): string => {
  // Simulate historical trend (in real app, this would come from API)
  const history = Array.from({ length: 10 }, (_, i) => {
    const variance = (Math.random() - 0.5) * 0.1;
    return Math.max(0, psi + variance - (i * 0.02));
  }).reverse();
  
  const width = 60;
  const height = 20;
  const max = Math.max(...history, 0.5);
  
  const points = history.map((val, i) => {
    const x = (i / (history.length - 1)) * width;
    const y = height - (val / max) * height;
    return `${x},${y}`;
  }).join(' ');
  
  return points;
};

const getStatusInfo = (psi: number) => {
  if (psi >= 0.3) return { label: 'SEVERE', color: 'bg-rose-500/10 text-rose-400 border-rose-500/30' };
  if (psi >= 0.2) return { label: 'HIGH', color: 'bg-orange-500/10 text-orange-400 border-orange-500/30' };
  if (psi >= 0.1) return { label: 'MILD', color: 'bg-amber-500/10 text-amber-400 border-amber-500/30' };
  return { label: 'NORMAL', color: 'bg-slate-500/10 text-slate-400 border-slate-500/30' };
};

const getBarColor = (psi: number) => {
  if (psi >= 0.3) return 'bg-rose-500';
  if (psi >= 0.2) return 'bg-orange-500';
  if (psi >= 0.1) return 'bg-amber-500';
  return 'bg-slate-600';
};

export const DriftChart: React.FC<DriftChartProps> = ({ driftData }) => {
  const features = Object.entries(driftData)
    .map(([feature, psi]) => ({ feature, psi }))
    .sort((a, b) => b.psi - a.psi)
    .slice(0, 10);

  return (
    <div className="w-full">
      {/* Legend */}
      <div className="flex items-center gap-4 mb-4 text-[10px] font-medium">
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-slate-600" />
          <span className="text-slate-500">Normal &lt; 0.10</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-amber-500" />
          <span className="text-slate-500">Mild ≥ 0.10</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-orange-500" />
          <span className="text-slate-500">High ≥ 0.20</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-rose-500" />
          <span className="text-slate-500">Severe ≥ 0.30</span>
        </div>
      </div>

      {/* Table */}
      <div className="border border-slate-800 rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-slate-900/50 border-b border-slate-800">
            <tr>
              <th className="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider w-12">#</th>
              <th className="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider">Feature</th>
              <th className="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider w-32">PSI Score</th>
              <th className="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider w-32">Status</th>
              <th className="text-left px-4 py-3 text-[10px] font-bold text-slate-500 uppercase tracking-wider w-24">Trend</th>
            </tr>
          </thead>
          <tbody>
            {features.map((item, idx) => {
              const status = getStatusInfo(item.psi);
              const barColor = getBarColor(item.psi);
              const sparklinePoints = generateSparkline(item.psi);
              
              return (
                <tr key={item.feature} className="border-b border-slate-800/50 hover:bg-slate-800/20 transition-colors">
                  <td className="px-4 py-3 text-sm text-slate-500 font-mono">{idx + 1}</td>
                  <td className="px-4 py-3 text-sm text-white font-medium">{item.feature}</td>
                  <td className="px-4 py-3">
                    <div className="space-y-1">
                      <div className="text-sm font-bold text-white font-mono">{item.psi.toFixed(2)}</div>
                      <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                        <div 
                          className={`h-full ${barColor} transition-all duration-500`}
                          style={{ width: `${Math.min(item.psi * 100, 100)}%` }}
                        />
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex px-2 py-1 rounded text-[9px] font-bold uppercase border ${status.color}`}>
                      {status.label}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <svg width="60" height="20" className="opacity-70">
                      <polyline
                        points={sparklinePoints}
                        fill="none"
                        stroke={item.psi >= 0.2 ? '#f43f5e' : item.psi >= 0.1 ? '#f59e0b' : '#64748b'}
                        strokeWidth="1.5"
                      />
                    </svg>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div className="mt-4 flex items-center justify-between text-xs text-slate-500">
        <span>Showing {features.length} of {Object.keys(driftData).length} features</span>
        <button className="text-emerald-500 hover:text-emerald-400 transition-colors">
          View Full Report →
        </button>
      </div>
    </div>
  );
};
