import { apiRequest } from './client'
import type {
  Cast,
  DrawRequest,
  IChingCastRequest,
  Note,
  ReadingContext,
  ReadingCreate,
  ReadingSummary,
} from './types'

export const readingsApi = {
  list: () => apiRequest<ReadingSummary[]>('/api/v1/readings'),
  context: (id: string) => apiRequest<ReadingContext>(`/api/v1/readings/${id}/context`),
  create: (body: ReadingCreate) =>
    apiRequest<ReadingSummary>('/api/v1/readings', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  draw: (id: string, body: DrawRequest) =>
    apiRequest<Cast>(`/api/v1/readings/${id}/casts/draw`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  castIChing: (id: string, body: IChingCastRequest) =>
    apiRequest<Cast>(`/api/v1/readings/${id}/casts/iching`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  addNote: (id: string, body: string) =>
    apiRequest<Note>(`/api/v1/readings/${id}/notes`, {
      method: 'POST',
      body: JSON.stringify({ body }),
    }),
  updateNote: (id: string, noteId: string, body: string) =>
    apiRequest<Note>(`/api/v1/readings/${id}/notes/${noteId}`, {
      method: 'PATCH',
      body: JSON.stringify({ body }),
    }),
  deleteNote: (id: string, noteId: string) =>
    apiRequest<void>(`/api/v1/readings/${id}/notes/${noteId}`, { method: 'DELETE' }),
}
