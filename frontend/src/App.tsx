import React, { useState, useCallback, useEffect } from 'react';
import { Plus, Menu, X, MessageSquare } from 'lucide-react';
import { ChatWindow } from './components/chat/ChatWindow';
import { ChatInputBox } from './components/chat/ChatInputBox';
import { DataSourceSelector } from './components/sidebar/DataSourceSelector';
import { MCPConfigPanel } from './components/sidebar/MCPConfigPanel';
import { Button } from './components/common/Button';
import { DataSource, MCPConfig, Message, Conversation, ThoughtStep, EntityResult, Reference } from './types';

function App() {
  const [userId] = useState(() => Math.random().toString(36).substring(2));
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [loading, setLoading] = useState(false);
  
  const [dataSources, setDataSources] = useState<DataSource[]>([]);

  useEffect(() => {
    const fetchDataSource = async () => {
      try {
        const backendUrl = import.meta.env.VITE_BACKEND_URL || "http://127.0.0.1:9800";
        const response = await fetch(`${backendUrl}/get_data_source`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setDataSources(data);
      } catch (e) {
        console.error("Fetch data source error: ", e);
      }
    };
    fetchDataSource();
  }, []);


  const [mcpConfigs, setMCPConfigs] = useState<MCPConfig[]>([
    { id: '1', name: 'Medical Entity Extraction', description: 'Extract drugs, diseases, symptoms', enabled: false },
    { id: '2', name: 'Literature Search', description: 'Search medical literature', enabled: false },
    { id: '3', name: 'Drug Interaction Checker', description: 'Check for drug interactions', enabled: false }
  ]);

  const [selectedSources, setSelectedSources] = useState<string[]>(["search_document_db","search_personal_db","search_guideline_db"]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [customMcpUrl, setCustomMcpUrl] = useState('');
  const [validationStatus, setValidationStatus] = useState<{ status: 'idle' | 'validating' | 'success' | 'error'; message: string }>({ status: 'idle', message: '' });
  const [customMcpTools, setCustomMcpTools] = useState<any[]>([]);

  const handleValidateMcp = useCallback(async () => {
    if (!customMcpUrl) {
      setValidationStatus({ status: 'error', message: 'URL cannot be empty.' });
      setCustomMcpTools([]);
      return;
    }
    setValidationStatus({ status: 'validating', message: 'Validating...' });
    setCustomMcpTools([]);
    try {
      const backendUrl = import.meta.env.VITE_BACKEND_URL || "http://127.0.0.1:9800";
      const response = await fetch(`${backendUrl}/validate_mcp`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: customMcpUrl }),
      });
      const data = await response.json();
      if (data.status === 'ok') {
        setValidationStatus({ status: 'success', message: data.message });
        setCustomMcpTools(data.tools || []);
      } else {
        setValidationStatus({ status: 'error', message: data.message });
      }
    } catch (error) {
      setValidationStatus({ status: 'error', message: 'Failed to connect to the validation server.' });
    }
  }, [customMcpUrl]);

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

    const newMessages: Message[] = [...messages, userMessage];
    setMessages(newMessages);
    setLoading(true);

    const agentMessageId = (Date.now() + 1).toString();
    setMessages(prev => [...prev, {
      id: agentMessageId,
      type: 'agent',
      content: '',
      timestamp: new Date(),
      streaming: true,
      thoughts: [],
      references: [],
      entities: [],
    }]);

    try {
      const backendUrl = import.meta.env.VITE_BACKEND_URL || "http://127.0.0.1:9800";
      const response = await fetch(`${backendUrl}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({
          userId: userId, 
          messages: newMessages.map(m => ({ role: m.type === 'agent' ? 'ai' : 'user', content: m.content })),
          attachment: {
            tools: selectedSources,
          },
        }),
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      
      let buffer = '';
      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          break;
        }
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data:')) {
            const jsonStr = line.substring(5).trim();
            if (jsonStr.includes('[stop]')) continue;
            
            try {
              const data = JSON.parse(jsonStr);
              setMessages(prev => prev.map(msg => {
                if (msg.id === agentMessageId) {
                  const newMsg = { ...msg };
                  switch (data.type) {
                    case 4: // text or entity data
                      try {
                        const potentialJson = JSON.parse(data.message);
                        // Check if this is entity data
                        if (potentialJson.diseases && Array.isArray(potentialJson.diseases)) {
                           newMsg.entities = potentialJson.diseases.map((d: any) => ({
                            id: d.id.toString(),
                            type: 'disease',
                            name: d.disease_name,
                            description: d.overview,
                            properties: {},
                          }));
                        } else {
                          // Not entity data, so treat as plain text that happens to be valid JSON
                          newMsg.content += data.message;
                        }
                      } catch (e) {
                        // Not a JSON object, so it's just text
                        newMsg.content += data.message;
                      }
                      break;
                    case 5: // tool status or references
                      try {
                        const toolData = JSON.parse(data.message);
                        if (Array.isArray(toolData) && toolData.length > 0) {
                          if (toolData[0].data && Array.isArray(toolData[0].data)) {
                            newMsg.references = toolData;
                          } else {
                            newMsg.thoughts = newMsg.thoughts ? [...newMsg.thoughts] : [];
                            toolData.forEach(tool => {
                              const existingThoughtIndex = newMsg.thoughts.findIndex(t => t.id === tool.id);
                              if (existingThoughtIndex > -1) {
                                newMsg.thoughts[existingThoughtIndex] = {
                                  ...newMsg.thoughts[existingThoughtIndex],
                                  content: tool.display,
                                  status: tool.status,
                                  func_output: tool.func_output,
                                };
                              } else {
                                newMsg.thoughts.push({
                                  id: tool.id,
                                  type: 'tool',
                                  content: tool.display,
                                  timestamp: new Date(),
                                  name: tool.name,
                                  globalization: tool.globalization,
                                  status: tool.status,
                                  func_output: tool.func_output,
                                });
                              }
                            });
                          }
                        }
                      } catch (e) {
                        console.error('Error parsing tool/reference data:', e);
                      }
                      break;
                    case 6: // metadata
                      console.log(`Received data type 6:`, JSON.parse(data.message));
                      break;
                    case 7: // entities
                      try {
                        const entityData = JSON.parse(data.message);
                        if (entityData.diseases && Array.isArray(entityData.diseases)) {
                          newMsg.entities = entityData.diseases.map((d: any) => ({
                            id: d.id.toString(),
                            type: 'disease',
                            name: d.disease_name,
                            description: d.overview,
                            properties: {},
                          }));
                        }
                      } catch (e) {
                        console.error('Error parsing entity data:', e);
                      }
                      break;
                  }
                  return newMsg;
                } 
                return msg;
              }));
            } catch (e) {
              // This might be a malformed JSON or a non-JSON message part
              console.error('Error parsing SSE data chunk:', jsonStr, e);
            }
          } else if (line.startsWith('event: end')) {
            return;
          }
        } 
      }
    } catch (error) {
      console.error('Chat request failed:', error);
      setMessages(prev => prev.map(msg => 
        msg.id === agentMessageId 
          ? { ...msg, content: 'An error occurred. Please try again.', streaming: false }
          : msg
      ));
    } finally {
      setLoading(false);
      setMessages(prev => prev.map(msg => 
        msg.id === agentMessageId 
          ? { ...msg, streaming: false }
          : msg
      ));
    }
  }, [messages, selectedSources]);

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

            <div className="space-y-2">
              <h3 className="text-sm font-medium text-gray-900">Add Custom MCP</h3>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={customMcpUrl}
                  onChange={(e) => setCustomMcpUrl(e.target.value)}
                  placeholder="Enter MCP SSE URL"
                  className="w-full px-3 py-2 text-sm text-gray-900 bg-white border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <Button onClick={handleValidateMcp} disabled={validationStatus.status === 'validating'}>
                  {validationStatus.status === 'validating' ? 'Validating...' : 'Validate'}
                </Button>
              </div>
              {validationStatus.message && (
                <p className={`text-sm ${validationStatus.status === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                  {validationStatus.message}
                </p>
              )}
              {validationStatus.status === 'success' && customMcpTools.length > 0 && (
                <div className="mt-2 p-2 border rounded-md bg-gray-50">
                  <h4 className="text-xs font-semibold text-gray-700">Available Tools:</h4>
                  <ul className="mt-1 text-xs text-gray-600 list-disc list-inside">
                    {customMcpTools.map((tool: any) => (
                      <li key={tool.name}>{tool.name}: {tool.description}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

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
