import React, { useState } from 'react';
import { ChevronDown, Pill, Activity, AlertCircle, ExternalLink } from 'lucide-react';
import { EntityResult } from '../../types';

interface EntityLinkedBlockProps {
  entities: EntityResult[];
}

export const EntityLinkedBlock: React.FC<EntityLinkedBlockProps> = ({ entities }) => {
  const [expandedEntity, setExpandedEntity] = useState<string | null>(null);

  const getEntityIcon = (type: EntityResult['type']) => {
    switch (type) {
      case 'drug':
        return <Pill className="w-4 h-4" />;
      case 'disease':
        return <Activity className="w-4 h-4" />;
      case 'symptom':
        return <AlertCircle className="w-4 h-4" />;
      default:
        return <Activity className="w-4 h-4" />;
    }
  };

  const getEntityColor = (type: EntityResult['type']) => {
    switch (type) {
      case 'drug':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      case 'disease':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'symptom':
        return 'text-orange-600 bg-orange-50 border-orange-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  if (entities.length === 0) return null;

  return (
    <div className="mt-4 space-y-2">
      <div className="text-sm font-medium text-gray-600 mb-3">
        Related Medical Information
      </div>
      
      {entities.map((entity) => (
        <div
          key={entity.id}
          className={`border rounded-lg transition-all duration-200 hover:shadow-sm ${getEntityColor(entity.type)}`}
        >
          <button
            onClick={() => setExpandedEntity(expandedEntity === entity.id ? null : entity.id)}
            className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-opacity-50 transition-colors"
          >
            <div className="flex items-center gap-3">
              {getEntityIcon(entity.type)}
              <div>
                <div className="font-medium text-sm">{entity.name}</div>
                <div className="text-xs opacity-75 capitalize">{entity.type}</div>
              </div>
            </div>
            <ChevronDown
              className={`w-4 h-4 transition-transform duration-200 ${
                expandedEntity === entity.id ? 'rotate-180' : ''
              }`}
            />
          </button>

          {expandedEntity === entity.id && (
            <div className="px-4 pb-4 space-y-3">
              <div className="text-sm text-gray-700 leading-relaxed bg-white p-3 rounded-lg border border-current border-opacity-20">
                {entity.description}
              </div>

              {Object.keys(entity.properties).length > 0 && (
                <div className="bg-white p-3 rounded-lg border border-current border-opacity-20">
                  <div className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                    Properties
                  </div>
                  <div className="grid grid-cols-1 gap-2">
                    {Object.entries(entity.properties).map(([key, value]) => (
                      <div key={key} className="flex justify-between items-start text-xs">
                        <span className="font-medium text-gray-600 capitalize">
                          {key.replace(/_/g, ' ')}:
                        </span>
                        <span className="text-gray-800 ml-2 text-right flex-1">
                          {Array.isArray(value) ? value.join(', ') : String(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {entity.references && entity.references.length > 0 && (
                <div className="space-y-2">
                  <div className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                    References
                  </div>
                  <div className="space-y-1">
                    {entity.references.map((ref) => (
                      <div key={ref.id} className="flex items-center gap-2 p-2 bg-white rounded-lg border border-current border-opacity-10">
                        <div className="flex-1 min-w-0">
                          <div className="text-xs font-medium text-gray-900 truncate">
                            [{ref.source}] {ref.title}
                          </div>
                        </div>
                        {ref.url && (
                          <ExternalLink className="w-3 h-3 text-gray-400 flex-shrink-0" />
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
};