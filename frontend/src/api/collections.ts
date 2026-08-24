import { apiRequest } from './client'
import type { Collection, CorpusStatus, Spread } from './types'

export const collectionsApi = {
  list: () => apiRequest<Collection[]>('/api/v1/collections'),
  spreads: () => apiRequest<Spread[]>('/api/v1/spreads'),
}

export const healthApi = () => apiRequest<{ status: string }>('/api/v1/health')
export const corpusStatusApi = () => apiRequest<CorpusStatus>('/api/v1/corpus-status')
