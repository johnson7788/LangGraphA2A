import React, { useState, useEffect } from 'react';
import { Bot, ExternalLink, ChevronDown } from 'lucide-react';
import { Message } from '../../types';
import { ThoughtCard } from './ThoughtCard';
import { EntityLinkedBlock } from './EntityLinkedBlock';

interface AgentMessageProps {
  message: Message;
}

export const AgentMessage: React.FC<AgentMessageProps> = ({ message }) => {
  const [displayedContent, setDisplayedContent] = useState('');
  const [showThoughts, setShowThoughts] = useState(false);
  const [currentThoughtIndex, setCurrentThoughtIndex] = useState(0);

  // Simulate streaming text effect
  useEffect(() => {
    if (message.streaming) {
      let index = 0;
      const interval = setInterval(() => {
        if (index < message.content.length) {
          setDisplayedContent(message.content.slice(0, index + 1));
          index++;
        } else {
          clearInterval(interval);
        }
      }, 20);
      return () => clearInterval(interval);
    } else {
      setDisplayedContent(message.content);
    }
  }, [message.content, message.streaming]);

  // Simulate thought process streaming
  useEffect(() => {
    if (message.thoughts && message.thoughts.length > 0) {
      const timer = setTimeout(() => {
        if (currentThoughtIndex < message.thoughts.length - 1) {
          setCurrentThoughtIndex(currentThoughtIndex + 1);
        }
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [currentThoughtIndex, message.thoughts]);

  const getReferenceBadgeColor = (source: string) => {
    const colors = {
      'Wiki': 'bg-blue-100 text-blue-800',
      'Database': 'bg-green-100 text-green-800',
      'Literature': 'bg-purple-100 text-purple-800',
      'Knowledge Base': 'bg-orange-100 text-orange-800',
    };
    return colors[source as keyof typeof colors] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="flex gap-4 mb-6 animate-fade-in">
      <div className="flex-shrink-0">
        <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-full flex items-center justify-center">
          <Bot className="w-4 h-4 text-white" />
        </div>
      </div>
      
      <div className="flex-1 space-y-4">
        {/* Thought Process Section */}
        {message.thoughts && message.thoughts.length > 0 && (
          <div className="space-y-3">
            <button
              onClick={() => setShowThoughts(!showThoughts)}
              className="flex items-center gap-2 text-sm font-medium text-gray-600 hover:text-gray-800 transition-colors"
            >
              <ChevronDown
                className={`w-4 h-4 transition-transform duration-200 ${
                  showThoughts ? 'rotate-180' : ''
                }`}
              />
              Thought Process ({message.thoughts.length} steps)
            </button>
            
            {showThoughts && (
              <div className="space-y-3 pl-4 border-l-2 border-gray-200">
                {message.thoughts.slice(0, currentThoughtIndex + 1).map((thought, index) => (
                  <ThoughtCard
                    key={thought.id}
                    thought={thought}
                    index={index}
                    isExpanded={index === 0}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {/* Main Response */}
        <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
          <div className="prose max-w-none text-gray-800 leading-relaxed">
            {displayedContent}
            {message.streaming && (
              <span className="inline-block w-1 h-4 bg-blue-500 ml-1 animate-pulse" />
            )}
          </div>
          
          {/* References */}
          {message.references && message.references.length > 0 && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              <div className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
                References
              </div>
              <div className="flex flex-wrap gap-2">
                {message.references.map((ref, index) => (
                  <span
                    key={ref.id}
                    className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${getReferenceBadgeColor(ref.source)}`}
                  >
                    [{ref.source}]
                    {ref.url && <ExternalLink className="w-3 h-3" />}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Entity Results */}
        {message.entities && message.entities.length > 0 && (
          <EntityLinkedBlock entities={message.entities} />
        )}
      </div>
    </div>
  );
};