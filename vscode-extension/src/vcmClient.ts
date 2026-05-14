import * as vscode from 'vscode';

export interface VcmMemory {
  memory_id: string;
  type: string;
  score?: number;
  text: string;
  validity?: string;
  timestamp?: string;
}

export interface VcmProjectState {
  project_id: string;
  total_memories: number;
  active_decisions: Array<{ id: string; text: string }>;
  recent_errors: Array<{ id: string; text: string }>;
  active_goals: Array<{ id: string; text: string }>;
}

export interface VcmHealth {
  basic: {
    events: number;
    memories: number;
    projects: number;
  };
  score: number;
}

export class VcmClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  private async fetch(path: string, options?: RequestInit): Promise<any> {
    const url = `${this.baseUrl}${path}`;
    try {
      const resp = await fetch(url, {
        ...options,
        headers: {
          'Content-Type': 'application/json',
          ...(options?.headers || {}),
        },
      });
      if (!resp.ok) {
        throw new Error(`VCM API error: ${resp.status} ${resp.statusText}`);
      }
      return await resp.json();
    } catch (err) {
      throw new Error(`VCM connection failed: ${err}`);
    }
  }

  async health(): Promise<VcmHealth> {
    return this.fetch('/health');
  }

  async searchMemory(projectId: string, query: string, limit: number = 10): Promise<VcmMemory[]> {
    const data = await this.fetch('/memory/read', {
      method: 'POST',
      body: JSON.stringify({ project_id: projectId, query, task_type: 'general' }),
    });
    // memory_read returns List[MemoryObject]
    if (!Array.isArray(data)) return [];
    return data.slice(0, limit).map((m: any) => ({
      memory_id: m.memory_id,
      type: m.memory_type?.value || m.memory_type || 'unknown',
      text: m.raw_text || m.compressed_summary || '',
      validity: m.validity,
      timestamp: m.timestamp,
    }));
  }

  async getProjectState(projectId: string): Promise<VcmProjectState> {
    return this.fetch(`/project/${encodeURIComponent(projectId)}/state`);
  }

  async ingestEvent(projectId: string, sessionId: string, eventType: string, rawText: string, payload?: any): Promise<any> {
    return this.fetch('/events', {
      method: 'POST',
      body: JSON.stringify({
        project_id: projectId,
        session_id: sessionId,
        event_type: eventType,
        raw_text: rawText,
        payload: payload || {},
      }),
    });
  }

  async correctMemory(memoryId: string, action: string, reason: string = ''): Promise<any> {
    return this.fetch('/memory/correct', {
      method: 'POST',
      body: JSON.stringify({ memory_id: memoryId, action, reason }),
    });
  }

  async buildContext(projectId: string, query: string, sessionId?: string, budget?: number): Promise<any> {
    return this.fetch('/context/build', {
      method: 'POST',
      body: JSON.stringify({
        project_id: projectId,
        session_id: sessionId,
        query,
        max_pack_tokens: budget || 500,
      }),
    });
  }
}
