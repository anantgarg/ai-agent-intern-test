export type DocumentStatus = "active" | "superseded" | "draft" | string;
export type PolicyAuthority = "official" | "none" | string;
export type Audience = "customer" | "internal" | string;

export interface DocumentFrontMatter {
  document_id?: string;
  title?: string;
  status?: DocumentStatus;
  effective_date?: string;
  last_reviewed?: string;
  superseded_date?: string;
  superseded_by?: string;
  supersedes?: string;
  audience?: Audience;
  policy_authority?: PolicyAuthority;
  customer_answering?: boolean;
  [key: string]: unknown;
}

export interface ParsedDocument {
  filename: string;
  filepath: string;
  frontMatter: DocumentFrontMatter;
  body: string;
}

export interface Chunk {
  id: string;
  filename: string;
  documentId: string;
  title: string;
  heading: string;
  headingPath: string[];
  text: string;
  metadata: DocumentFrontMatter;
  authorityScore: number;
}

export interface RetrievedChunk extends Chunk {
  bm25Score: number;
  finalScore: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface SourceRef {
  filename: string;
  heading: string;
}

export interface ToolCallRecord {
  name: string;
  arguments: Record<string, unknown>;
  result: unknown;
}

export interface AgentTurnResult {
  answer: string;
  sources: SourceRef[];
  handoff: boolean;
  toolCalls: ToolCallRecord[];
  retrieved: RetrievedChunk[];
  abstained: boolean;
}

export interface TraceEvent {
  timestamp: string;
  sessionId: string;
  userMessage: string;
  history: ChatMessage[];
  retrieved: Array<{
    filename: string;
    heading: string;
    documentId: string;
    status?: string;
    policy_authority?: string;
    audience?: string;
    bm25Score: number;
    finalScore: number;
    preview: string;
  }>;
  toolCalls: ToolCallRecord[];
  finalResponse: string;
  sources: SourceRef[];
  handoff: boolean;
  error?: string;
}

export interface SafeOrderView {
  order_id: string;
  membership_tier: string;
  items: Array<{ name: string; quantity: number; final_sale: boolean }>;
  placed_at: string;
  status: string;
  status_updated_at: string;
  shipped_at: string | null;
  delivered_at: string | null;
  carrier: string | null;
  tracking_number: string | null;
  estimated_delivery: string | null;
  customer_safe_message: string;
  notes: string[];
}

export interface OrderLookupResult {
  found: boolean;
  order_id_normalized: string | null;
  order?: SafeOrderView;
  error?: string;
}

export interface EvalExpect {
  must_include?: string[];
  must_not_include?: string[];
  must_include_concepts?: string[];
  must_ask_for?: string[];
  must_not_invent?: string[];
  must_refuse_to_disclose?: string[];
  must_not_follow?: string[];
  required_sources?: string[];
  forbidden_sources_as_authority?: string[];
  tool?: string;
  tool_arguments?: Record<string, string>;
  handoff?: boolean;
  must_not_silently_choose_one?: boolean;
}

export interface EvalCase {
  id: string;
  category: string;
  messages: Array<{ role: "user"; content: string }>;
  expect: EvalExpect;
}

export interface EvalCaseResult {
  id: string;
  category: string;
  passed: boolean;
  failures: string[];
  answer: string;
  sources: SourceRef[];
  handoff: boolean;
  toolCalls: ToolCallRecord[];
}
