import { useState, useEffect } from 'react';
import axios from 'axios';
import type { PipelineStatus, HistoryEntry, ModelInfo } from './types';

export function usePipeline() {
  const [status, setStatus] = useState<PipelineStatus | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [driftReports, setDriftReports] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const [statusRes, historyRes, modelsRes] = await Promise.all([
        axios.get('/pipeline/status'),
        axios.get('/pipeline/history'),
        axios.get('/models')
      ]);
      setStatus(statusRes.data);
      setHistory(historyRes.data);
      setModels(modelsRes.data);
      
      // Fetch drift reports if pipeline is running
      if (statusRes.data.running) {
        try {
          const driftRes = await axios.get('/drift/check');
          setDriftReports(driftRes.data);
        } catch (err) {
          // Drift endpoint might not be available
        }
      }
    } catch (error) {
      console.error("Failed to fetch pipeline data", error);
    } finally {
      setLoading(false);
    }
  };

  const startPipeline = async (scenario: string = "normal") => {
    try {
      await axios.post(`/pipeline/start?scenario=${scenario}`);
      setTimeout(fetchData, 500);
    } catch (error) {
      console.error("Failed to start pipeline", error);
    }
  };

  const stopPipeline = async () => {
    try {
      await axios.post('/pipeline/stop');
      setTimeout(fetchData, 500);
    } catch (error) {
      console.error("Failed to stop pipeline", error);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 2000);
    return () => clearInterval(interval);
  }, []);

  return { 
    status, 
    history, 
    models, 
    driftReports,
    loading, 
    startPipeline, 
    stopPipeline,
    refresh: fetchData 
  };
}
