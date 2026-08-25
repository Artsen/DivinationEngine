import { apiRequest } from './client'
import type { Spread, SpreadCreate, SpreadPatch } from './types'

export const spreadsApi = {
  list: () => apiRequest<Spread[]>('/api/v1/spreads'),
  get: (id: string) => apiRequest<Spread>(`/api/v1/spreads/${id}`),
  create: (body: SpreadCreate) => apiRequest<Spread>('/api/v1/spreads', {
    method: 'POST',
    body: JSON.stringify(body),
  }),
  update: (id: string, body: SpreadPatch) => apiRequest<Spread>(`/api/v1/spreads/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  }),
}
