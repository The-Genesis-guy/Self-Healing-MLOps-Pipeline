import React from 'react';
import { Swords, Sparkles } from 'lucide-react';
import type { PipelineStatus } from '../types';

interface ShadowArenaProps {
  status: PipelineStatus;
}

export const ShadowArena: React.FC<ShadowArenaProps> = ({ status }) => {
  if (!status.shadow_model_version) return null;

  return (
    <div className="p-6 rounded-xl border border-amber-500/30 bg-amber-500/5 relative overflow-hidden shadow-[0_0_30px_rgba(245,158,11,0.1)]">
      {/* Background Decorative Glow */}
      <div className="absolute top-0 right-0 w-48 h-48 bg-amber-500/10 blur-[80px] -mr-24 -mt-24" />
      
      <div className="relative z-10">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-amber-500" />
            <h3 className="text-xs font-bold text-amber-400 uppercase tracking-wider">
              GUARDIAN GATE <span className="text-emerald-500">[LIVE]</span>
            </h3>
          </div>
          <div className="text-[10px] text-slate-500">Comparing Models...</div>
        </div>

        {/* Comparison */}
        <div className="flex items-center justify-between gap-6">
          {/* Current Model */}
          <div className="flex-1 p-4 rounded-lg bg-slate-900/80 border border-slate-800 text-center">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-2">
              Current (v{status.active_model_version})
            </div>
            <div className="text-3xl font-black text-white mb-1">
              {(status.active_model_f1 || 0).toFixed(2)}
            </div>
            <div className="text-[10px] text-slate-600">F1-Score</div>
          </div>

          {/* VS */}
          <div className="flex flex-col items-center">
            <div className="p-2 bg-amber-500 rounded-full shadow-[0_0_15px_rgba(245,158,11,0.5)]">
              <Swords className="w-5 h-5 text-slate-900" />
            </div>
            <div className="text-amber-500 font-black text-sm mt-1">VS</div>
          </div>

          {/* New Model */}
          <div className="flex-1 p-4 rounded-lg bg-amber-500/10 border border-amber-500/40 text-center">
            <div className="text-[10px] text-amber-400 uppercase tracking-wider mb-2">
              New (v{status.shadow_model_version})
            </div>
            <div className="text-3xl font-black text-emerald-400 mb-1">0.54</div>
            <div className="text-[10px] text-amber-600">In Trial...</div>
          </div>
        </div>

        {/* Action Button */}
        <div className="mt-4">
          <button className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 rounded-lg transition-all text-sm shadow-[0_0_15px_rgba(16,185,129,0.2)]">
            PROMOTE: New model is better by +0.03
          </button>
        </div>

        {/* Progress */}
        <div className="mt-4 p-3 rounded-lg bg-slate-900/50 border border-slate-800">
          <div className="flex items-center justify-between text-[10px] text-slate-400 mb-2">
            <span>Retraining in Progress...</span>
            <span className="font-mono">68%</span>
          </div>
          <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
            <div 
              className="h-full bg-emerald-500 rounded-full transition-all duration-500"
              style={{ width: '68%' }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};
