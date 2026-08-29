export interface Document {
  id: string;
  original_file_name: string;
  status: 'uploaded' | 'processing' | 'ready' | 'failed' | 'deleting';
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

export interface SourceCitation {
  document_id: string;
  original_file_name: string;
  chunk_index: number;
  page_number?: number | null;
  section?: string | null;
}

export interface Message {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  created_at?: string;
  error?: string;
  sources?: SourceCitation[];
}
