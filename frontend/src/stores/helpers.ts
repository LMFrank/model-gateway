import { isAxiosError } from 'axios'

export const extractErrorMessage = (error: unknown, fallback: string): string => {
  if (isAxiosError(error)) {
    const detail = (error.response?.data as { detail?: string } | undefined)?.detail
    return detail || error.message || fallback
  }
  if (error instanceof Error) return error.message
  return fallback
}
