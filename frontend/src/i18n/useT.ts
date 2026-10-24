import { useCallback } from 'react'
import { useCaseState, type UiLang } from '../state/caseState'
import { en, type MessageKey, type Messages } from './en'
import { es } from './es'

const dictionaries: Record<UiLang, Messages> = { en, es }

export function useT() {
  const { state } = useCaseState()
  const messages = dictionaries[state.caseInfo.lang]
  return useCallback((key: MessageKey) => messages[key], [messages])
}

// Replaces {name} placeholders in a message, e.g. fill(t('recordsFound'), { n: 3 }).
export function fill(message: string, vars: Record<string, string | number>): string {
  return message.replace(/\{(\w+)\}/g, (whole, name: string) => (name in vars ? String(vars[name]) : whole))
}
