import React from 'react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  ResponsiveContainer, 
  Cell,
  Tooltip
} from 'recharts';

interface ImportanceChartProps {
  importance: Record<string, number>;
}

export const ImportanceChart: React.FC<ImportanceChartProps> = ({ importance }) => {
  const data = Object.entries(importance).map(([feature, weight]) => ({
    feature,
    weight: parseFloat(weight.toFixed(4))
  })).sort((a, b) => b.weight - a.weight).slice(0, 8);

  return (
    <div className="w-full h-52">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart layout="vertical" data={data} margin={{ left: 8, right: 12 }}>
          <XAxis type="number" hide />
          <YAxis 
            dataKey="feature" 
            type="category" 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: '#94a3b8', fontSize: 10 }}
            width={122}
          />
          <Tooltip 
            cursor={{ fill: 'transparent' }}
            contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px' }}
          />
          <Bar dataKey="weight" radius={[0, 4, 4, 0]}>
            {data.map((_entry, index) => (
              <Cell key={`cell-${index}`} fill="#10b981" fillOpacity={0.8 - (index * 0.08)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};
