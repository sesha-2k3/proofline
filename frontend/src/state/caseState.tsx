import { createContext, useContext, useReducer, type Dispatch, type ReactNode } from 'react'

// UI language. Mirrors caseInfo.lang once CaseInfo is in the generated schema.
export type UiLang = 'en' | 'es'
export type Step = 1 | 2 | 3 | 4 | 5

// Case state lives only in memory (no localStorage/sessionStorage/cookies).
// Pending B4: caseInfo, documents, records, evaluation, exemptionAnswers,
// submissions, health, and rules are added here using types from
// src/api/schema.d.ts once shared/openapi.json contains them.
export interface CaseState {
  step: Step
  lang: UiLang
  demoMode: boolean
}

export type CaseAction =
  | { type: 'SET_STEP'; step: Step }
  | { type: 'SET_LANG'; lang: UiLang }
  | { type: 'SET_DEMO_MODE'; demoMode: boolean }
  | { type: 'RESET' }

const initialCaseState: CaseState = {
  step: 1,
  lang: 'en',
  demoMode: false,
}

function caseReducer(state: CaseState, action: CaseAction): CaseState {
  switch (action.type) {
    case 'SET_STEP':
      return { ...state, step: action.step }
    case 'SET_LANG':
      return { ...state, lang: action.lang }
    case 'SET_DEMO_MODE':
      return { ...state, demoMode: action.demoMode }
    case 'RESET':
      return { ...initialCaseState, lang: state.lang, demoMode: state.demoMode }
  }
}

interface CaseContextValue {
  state: CaseState
  dispatch: Dispatch<CaseAction>
}

const CaseContext = createContext<CaseContextValue | null>(null)

export function CaseProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(caseReducer, initialCaseState)
  return <CaseContext.Provider value={{ state, dispatch }}>{children}</CaseContext.Provider>
}

export function useCaseState(): CaseContextValue {
  const value = useContext(CaseContext)
  if (!value) throw new Error('useCaseState must be used inside CaseProvider')
  return value
}
