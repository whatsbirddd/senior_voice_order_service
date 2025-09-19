export const BACKEND_BASE = process.env.BACKEND_BASE || process.env.NEXT_PUBLIC_BACKEND_BASE || "http://localhost:8000";

// Agent API 호출 함수들
export interface AgentChatRequest {
  sessionId?: string;
  message: string;
  store?: string;
  selectedNames?: string[];
  profile?: {
    ageGroup?: string;
    allergies?: string[];
    diseases?: string[];
    prefers?: string[];
    dislikes?: string[];
  };
}

export interface AgentResponse {
  message: string;
  stage: string;
  order_items?: Array<{
    name: string;
    quantity: number;
    price: number;
  }>;
  total_amount?: number;
  suggestions?: string[];
  [key: string]: any;
}

export async function chatWithAgent(request: AgentChatRequest): Promise<AgentResponse> {
  const response = await fetch(`${BACKEND_BASE}/agent/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });
  if (!response.ok) {
    throw new Error(`Agent API error: ${response.status}`);
  }

  return await response.json();
}

export async function transcribeAudio(audioBlob: Blob): Promise<{ text: string; raw?: any }> {
  const formData = new FormData();
  formData.append("file", audioBlob, "audio.wav");

  const response = await fetch(`${BACKEND_BASE}/api/audio/transcribe`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    throw new Error(`Transcription API error: ${response.status}`);
  }

  return await response.json();
}

// 세션 ID 생성 함수
export function generateSessionId(): string {
  return `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}
