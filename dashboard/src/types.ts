export interface PipelineStatus {
  running: boolean;
  iteration: number;
  last_action: string;
  last_reason: string;
  last_drifted_features: string[];
  active_model_version: number | null;
  active_model_f1: number | null;
  shadow_model_version: number | null;
  health: 'healthy' | 'warning' | 'critical';
}

export interface ModelInfo {
  version: number;
  path: string;
  f1_score: number;
  trained_at: string;
  is_active: boolean;
  feature_importance?: Record<string, number>;
}

export interface HistoryEntry {
  iteration: number;
  timestamp: string;
  model_version: number | null;
  f1_score: number | null;
  drift_score: number;
  action: string;
  reason: string;
}
