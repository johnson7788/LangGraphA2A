import React from 'react';
import { Settings, ToggleLeft as Toggle } from 'lucide-react';
import { MCPConfig } from '../../types';

interface MCPConfigPanelProps {
  configs: MCPConfig[];
  onConfigChange: (configId: string, enabled: boolean) => void;
}

export const MCPConfigPanel: React.FC<MCPConfigPanelProps> = ({
  configs,
  onConfigChange
}) => {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm font-semibold text-gray-700">
        <Settings className="w-4 h-4" />
        MCP Configuration
      </div>
      
      <div className="space-y-2">
        {configs.map(config => (
          <div key={config.id} className="flex items-start justify-between p-3 bg-gray-50 border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors">
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-gray-900">
                {config.name}
              </div>
              <div className="text-xs text-gray-500 mt-0.5">
                {config.description}
              </div>
            </div>
            <button
              onClick={() => onConfigChange(config.id, !config.enabled)}
              className="ml-3 flex-shrink-0"
            >
              <div className={`relative inline-flex h-5 w-9 rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
                config.enabled ? 'bg-blue-600' : 'bg-gray-300'
              }`}>
                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-200 ${
                  config.enabled ? 'translate-x-4' : 'translate-x-0.5'
                } mt-0.5`} />
              </div>
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};