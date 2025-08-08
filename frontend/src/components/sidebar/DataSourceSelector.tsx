import React from 'react';
import { Database, BookOpen, FileText } from 'lucide-react';
import { Select } from '../common/Select';
import { DataSource } from '../../types';

interface DataSourceSelectorProps {
  dataSources: DataSource[];
  selectedSources: string[];
  onSelectionChange: (selectedIds: string[]) => void;
}

export const DataSourceSelector: React.FC<DataSourceSelectorProps> = ({
  dataSources,
  selectedSources,
  onSelectionChange
}) => {
  const getIcon = (type: DataSource['type']) => {
    switch (type) {
      case 'database':
        return <Database className="w-4 h-4" />;
      case 'knowledge_base':
        return <BookOpen className="w-4 h-4" />;
      case 'literature':
        return <FileText className="w-4 h-4" />;
      default:
        return <Database className="w-4 h-4" />;
    }
  };

  const options = dataSources.map(ds => ({
    value: ds.id,
    label: ds.name,
    description: ds.description
  }));

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm font-semibold text-gray-700">
        <Database className="w-4 h-4" />
        Data Sources
      </div>
      
      <Select
        options={options}
        value={selectedSources}
        onChange={onSelectionChange}
        placeholder="Select data sources..."
        multiple={true}
      />
      
      {selectedSources.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-medium text-gray-500 uppercase tracking-wider">
            Selected ({selectedSources.length})
          </div>
          <div className="space-y-1">
            {dataSources
              .filter(ds => selectedSources.includes(ds.id))
              .map(ds => (
                <div key={ds.id} className="flex items-center gap-2 p-2 bg-blue-50 border border-blue-200 rounded-lg">
                  {getIcon(ds.type)}
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-medium text-blue-900 truncate">
                      {ds.name}
                    </div>
                  </div>
                </div>
              ))
            }
          </div>
        </div>
      )}
    </div>
  );
};