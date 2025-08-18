export interface DataSource {
  id: string;
  name: string;
  description: string;
  type: 'database' | 'knowledge_base' | 'literature';
}

export interface MCPConfig {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
}

export interface Reference {
  id: string;
  source: string;
  title: string;
  url?: string;
  snippet?: string;
}

export interface ThoughtStep {
  id: string;
  type: 'query' | 'reasoning' | 'synthesis' | 'tool';
  content: string;
  timestamp: Date;
  references?: Reference[];
  name?: string;
  globalization?: string;
  status?: 'Working' | 'Done';
  func_output?: string;
}

export interface EntityResult {
  id: string;
  type: 'drug' | 'disease' | 'symptom';
  name: string;
  description: string;
  properties: Record<string, any>;
  references?: Reference[];
}

export interface Message {
  id: string;
  type: 'user' | 'agent';
  content: string;
  thoughts?: ThoughtStep[];
  references?: Reference[];
  entities?: EntityResult[];
  timestamp: Date;
  streaming?: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  dataSources: DataSource[];
  mcpConfigs: MCPConfig[];
  createdAt: Date;
}