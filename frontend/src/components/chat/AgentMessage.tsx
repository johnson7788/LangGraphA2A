import React, { useState } from 'react';
import { Bot, ChevronDown } from 'lucide-react';
import { Message } from '../../types';
import { ThoughtCard } from './ThoughtCard';
import { EntityLinkedBlock } from './EntityLinkedBlock';
import References from './References';

interface AgentMessageProps {
  message: Message;
}

export const AgentMessage: React.FC<AgentMessageProps> = ({ message }) => {
  const [showThoughts, setShowThoughts] = useState(false);

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
                {message.thoughts.map((thought, index) => (
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
            {message.content}
            {message.streaming && (
              <span className="inline-block w-1 h-4 bg-blue-500 ml-1 animate-pulse" />
            )}
          </div>
        </div>

        {/* References Display */}
        {message.references && message.references.length > 0 && (
          <References references={message.references} />
        )}

        {/* Entity Results */}
        {message.entities && message.entities.length > 0 && (
          <EntityLinkedBlock entities={message.entities} />
        )}
      </div>
    </div>
  );
};