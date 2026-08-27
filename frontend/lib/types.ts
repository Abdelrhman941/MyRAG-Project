export interface Document {
  id: string;
  original_file_name: string;
  status: 'uploaded' | 'processing' | 'ready' | 'failed';
  created_at: string;
  session_id?: string;
  content_hash?: string;
}

export interface Session {
  id: string;
  title?: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  created_at?: string;
  error?: string;
  sources?: Array<{
    document_name: string;
  }>;
}
