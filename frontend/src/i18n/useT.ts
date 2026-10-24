import { useCallback } from 'react'
import { useCaseState, type UiLang } from '../state/caseState'
import { en, type MessageKey, type Messages } from './en'
import { es } from './es'

const dictionaries: Record<UiLang, Messages> = { en, es }

export function useT() {
  const { state } = useCaseState()
  const messages = dictionaries[state.lang]
  return useCallback((key: MessageKey) => messages[key], [messages])
}
