import type { ReactNode } from 'react'

export function LoadingState({ children = 'Loading…' }: { children?: ReactNode }) {
  return <div className="state-panel" role="status">{children}</div>
}

export function ErrorState({ message }: { message: string }) {
  return <div className="state-panel state-panel--error" role="alert">{message}</div>
}
