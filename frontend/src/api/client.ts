const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

type ErrorBody = { detail?: string | Array<{ msg?: string }> }

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function errorMessage(body: ErrorBody | null, fallback: string): string {
  if (typeof body?.detail === 'string') return body.detail
  if (Array.isArray(body?.detail)) {
    return body.detail.map((row) => row.msg).filter(Boolean).join(' ') || fallback
  }
  return fallback
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
  })
  if (!response.ok) {
    let body: ErrorBody | null = null
    try {
      body = (await response.json()) as ErrorBody
    } catch {
      // The readable HTTP fallback below is enough for non-JSON failures.
    }
    const message = errorMessage(body, `Request failed (${response.status})`)
    console.error('DivinationEngine API request failed', response.status, path, body)
    throw new ApiError(response.status, message)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export function imageUrl(itemId: string): string {
  return `${API_BASE}/api/v1/items/${encodeURIComponent(itemId)}/image`
}
