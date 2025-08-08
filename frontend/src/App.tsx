import React, { useState, useCallback } from 'react';
import { Plus, Menu, X, MessageSquare } from 'lucide-react';
import { ChatWindow } from './components/chat/ChatWindow';
import { ChatInputBox } from './components/chat/ChatInputBox';
import { DataSourceSelector } from './components/sidebar/DataSourceSelector';
import { MCPConfigPanel } from './components/sidebar/MCPConfigPanel';
import { Button } from './components/common/Button';
import { DataSource, MCPConfig, Message, Conversation, ThoughtStep, EntityResult, Reference } from './types';

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [loading, setLoading] = useState(false);
  
  // Mock data
  const [dataSources] = useState<DataSource[]>([
    { id: '1', name: 'Disease Database', description: 'Comprehensive disease information', type: 'database' },
    { id: '2', name: 'Medical Literature', description: 'PubMed and medical journals', type: 'literature' },
    { id: '3', name: 'Drug Information', description: 'Pharmacological database', type: 'database' },
    { id: '4', name: 'User Knowledge Base', description: 'Custom medical knowledge', type: 'knowledge_base' }
  ]);

  const [mcpConfigs, setMCPConfigs] = useState<MCPConfig[]>([
    { id: '1', name: 'Medical Entity Extraction', description: 'Extract drugs, diseases, symptoms', enabled: true },
    { id: '2', name: 'Literature Search', description: 'Search medical literature', enabled: true },
    { id: '3', name: 'Drug Interaction Checker', description: 'Check for drug interactions', enabled: false }
  ]);

  const [selectedSources, setSelectedSources] = useState<string[]>(['1', '2']);
  const [messages, setMessages] = useState<Message[]>([]);

  const handleMCPConfigChange = useCallback((configId: string, enabled: boolean) => {
    setMCPConfigs(configs => 
      configs.map(config => 
        config.id === configId ? { ...config, enabled } : config
      )
    );
  }, []);

  const handleNewConversation = useCallback(() => {
    setMessages([]);
  }, []);

  const handleSendMessage = useCallback(async (content: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setLoading(true);

    // Simulate agent processing
    setTimeout(() => {
      const mockThoughts: ThoughtStep[] = [
        {
          id: '1',
          type: 'query',
          content: 'Searching selected data sources for information about the user\'s question...',
          timestamp: new Date(),
          references: [
            { id: '1', source: 'Database', title: 'Medical Knowledge Base Query', snippet: 'Found relevant entries' }
          ]
        },
        {
          id: '2',
          type: 'reasoning',
          content: 'Analyzing the retrieved information and cross-referencing with multiple sources to ensure accuracy.',
          timestamp: new Date()
        },
        {
          id: '3',
          type: 'synthesis',
          content: 'Synthesizing information from multiple sources to provide a comprehensive answer.',
          timestamp: new Date()
        }
      ];

      const mockEntities: EntityResult[] = [
        {
          id: '1',
          type: 'drug',
          name: 'Aspirin',
          description: 'A medication used to reduce pain, fever, or inflammation.',
          properties: {
            'Generic Name': 'Acetylsalicylic acid',
            'Drug Class': 'NSAIDs',
            'Common Uses': ['Pain relief', 'Fever reduction', 'Anti-inflammatory']
          },
          references: [
            { id: '1', source: 'Drug Database', title: 'Aspirin Monograph' }
          ]
        }
      ];

      const mockReferences: Reference[] = [
        { id: '1', source: 'Wiki', title: 'Medical Wikipedia Entry' },
        { id: '2', source: 'Database', title: 'Clinical Database Match' },
        { id: '3', source: 'Literature', title: 'Recent Research Study' }
      ];

      const agentMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: 'agent',
        content: `Based on the selected data sources, I can provide you with comprehensive information about your medical question. The analysis shows relevant clinical data and evidence-based recommendations.

This response incorporates information from multiple verified medical sources including peer-reviewed literature, clinical databases, and established medical knowledge bases to ensure accuracy and reliability.

The information provided should be used for educational purposes and does not replace professional medical advice. Always consult with qualified healthcare professionals for medical decisions.`,
        thoughts: mockThoughts,
        references: mockReferences,
        entities: content.toLowerCase().includes('aspirin') ? mockEntities : undefined,
        timestamp: new Date(),
        streaming: true
      };

      setMessages(prev => [...prev, agentMessage]);
      setLoading(false);
    }, 2000);
  }, []);

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Mobile backdrop */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div className={`fixed inset-y-0 left-0 z-50 w-80 bg-white border-r border-gray-200 transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static lg:inset-0 ${
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      }`}>
        <div className="flex flex-col h-full">
          {/* Sidebar Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center">
                <MessageSquare className="w-4 h-4 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-gray-900">AgentRAG</h1>
                <p className="text-xs text-gray-500">Medical Q&A System</p>
              </div>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden p-1 hover:bg-gray-100 rounded-md"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Sidebar Content */}
          <div className="flex-1 p-4 space-y-6 overflow-y-auto">
            <Button
              onClick={handleNewConversation}
              icon={Plus}
              className="w-full"
              variant="outline"
            >
              New Conversation
            </Button>

            <DataSourceSelector
              dataSources={dataSources}
              selectedSources={selectedSources}
              onSelectionChange={setSelectedSources}
            />

            <MCPConfigPanel
              configs={mcpConfigs}
              onConfigChange={handleMCPConfigChange}
            />
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-4 py-3">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 hover:bg-gray-100 rounded-md"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Medical Consultation</h2>
              <p className="text-sm text-gray-500">
                {selectedSources.length} data source{selectedSources.length !== 1 ? 's' : ''} selected
              </p>
            </div>
          </div>
        </div>

        {/* Chat Area */}
        <ChatWindow messages={messages} />

        {/* Input Area */}
        <ChatInputBox
          onSendMessage={handleSendMessage}
          loading={loading}
          disabled={selectedSources.length === 0}
        />
      </div>
    </div>
  );
}

export default App;