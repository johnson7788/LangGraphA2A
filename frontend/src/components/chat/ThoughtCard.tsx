import React, { useState } from 'react';
import { ChevronRight, PenTool as Tool, Brain, Search, Lightbulb, ExternalLink, Loader, CheckCircle } from 'lucide-react';
import { ThoughtStep } from '../../types';

interface ThoughtCardProps {
  thought: ThoughtStep;
  index: number;
  isExpanded?: boolean;
}

export const ThoughtCard: React.FC<ThoughtCardProps> = ({
  thought,
  index,
  isExpanded = false
}) => {
  const [expanded, setExpanded] = useState(isExpanded);

  const getIcon = (type: ThoughtStep['type'], status?: ThoughtStep['status']) => {
    switch (type) {
      case 'tool':
        return status === 'Done' 
          ? <CheckCircle className="w-4 h-4 text-emerald-600" /> 
          : <Loader className="w-4 h-4 animate-spin text-emerald-600" />;
      case 'reasoning':
        return <Brain className="w-4 h-4" />;
      case 'query':
        return <Search className="w-4 h-4" />;
      case 'synthesis':
        return <Lightbulb className="w-4 h-4" />;
      default:
        return <Brain className="w-4 h-4" />;
    }
  };

  const getTypeLabel = (type: ThoughtStep['type'], name?: string) => {
    if (type === 'tool') {
      return name || 'Tool';
    }
    switch (type) {
      case 'reasoning':
        return 'Reasoning';
      case 'query':
        return 'Query';
      case 'synthesis':
        return 'Synthesis';
      default:
        return 'Process';
    }
  };

  const getTypeColor = (type: ThoughtStep['type']) => {
    switch (type) {
      case 'tool':
        return 'text-emerald-600 bg-emerald-50 border-emerald-200';
      case 'reasoning':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      case 'query':
        return 'text-purple-600 bg-purple-50 border-purple-200';
      case 'synthesis':
        return 'text-amber-600 bg-amber-50 border-amber-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  return (
    <div className={`border rounded-lg transition-all duration-300 hover:shadow-md ${getTypeColor(thought.type)}`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center gap-3 text-left hover:bg-opacity-50 transition-colors"
      >
        <div className="flex items-center justify-center w-6 h-6 bg-white rounded-full border-2 border-current">
          <span className="text-xs font-bold">{index + 1}</span>
        </div>
        
        <div className="flex items-center gap-2 flex-1">
          {getIcon(thought.type, thought.status)}
          <span className="font-medium text-sm">
            {getTypeLabel(thought.type, thought.name)}
          </span>
          {thought.globalization && (
            <span className="text-xs px-2 py-0.5 bg-gray-200 text-gray-600 rounded-full">{thought.globalization}</span>
          )}
        </div>
        
        <ChevronRight 
          className={`w-4 h-4 transition-transform duration-200 ${
            expanded ? 'rotate-90' : ''
          }`}
        />
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3">
          <div className="text-sm text-gray-700 leading-relaxed bg-white p-3 rounded-lg border border-current border-opacity-20">
            {thought.content}
          </div>

          {thought.func_output && (
            <div className="space-y-2">
              <div className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                Tool Output
              </div>
              <pre className="text-xs text-gray-700 leading-relaxed bg-white p-3 rounded-lg border border-current border-opacity-20 whitespace-pre-wrap break-all">
                {thought.func_output}
              </pre>
            </div>
          )}
          
          {thought.references && thought.references.length > 0 && (
            <div className="space-y-2">
              <div className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                References
              </div>
              <div className="space-y-1">
                {thought.references.map((ref, idx) => (
                  <div key={ref.id} className="flex items-center gap-2 p-2 bg-white rounded-lg border border-current border-opacity-10">
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-medium text-gray-900 truncate">
                        [{ref.source}] {ref.title}
                      </div>
                      {ref.snippet && (
                        <div className="text-xs text-gray-500 mt-0.5 truncate">
                          {ref.snippet}
                        </div>
                      )}
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
  );
};