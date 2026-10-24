import { createContext, useContext, useReducer, type Dispatch, type ReactNode } from 'react'
import type {
  CaseInfo,
  Deadline,
  DocumentResult,
  EvaluateResponse,
  EvidenceRecord,
  ExemptionAnswer,
  HealthResponse,
  RulesResponse,
  SubmissionEntry,
} from '../api/client'

// UI language comes from caseInfo.lang.
export type UiLang = CaseInfo['lang']
export type Step = 1 | 2 | 3 | 4 | 5

export type DocumentStatus = 'queued' | 'uploading' | 'done' | 'error'

export interface CaseDocument {
  docId: string
  file: File
  objectUrl: string
  status: DocumentStatus
  result: DocumentResult | null
  error?: string
}

// Case state lives only in memory (no localStorage/sessionStorage/cookies).
export interface CaseState {
  caseInfo: CaseInfo
  documents: CaseDocument[]
  records: EvidenceRecord[]
  evaluation: EvaluateResponse | null
  // Last non-null evaluation before the current one, for Results transitions.
  priorEvaluation: EvaluateResponse | null
  // From POST /api/deadline, or evaluation.deadline after Evaluate.
  deadline: Deadline | null
  exemptionAnswers: ExemptionAnswer[]
  submissions: SubmissionEntry[]
  step: Step
  health: HealthResponse | null
  healthError: boolean
  rules: RulesResponse | null
}

export type CaseAction =
  | { type: 'SET_STEP'; step: Step }
  | { type: 'SET_LANG'; lang: UiLang }
  | { type: 'SET_CASE_INFO'; caseInfo: CaseInfo }
  | { type: 'ADD_DOCUMENT'; document: CaseDocument }
  | { type: 'UPDATE_DOCUMENT'; docId: string; changes: Partial<Omit<CaseDocument, 'docId'>> }
  | { type: 'REMOVE_DOCUMENT'; docId: string }
  | { type: 'SET_RECORDS'; records: EvidenceRecord[] }
  | { type: 'SET_EVALUATION'; evaluation: EvaluateResponse | null }
  | { type: 'SET_DEADLINE'; deadline: Deadline | null }
  | { type: 'SET_EXEMPTION_ANSWER'; answer: ExemptionAnswer }
  | { type: 'ADD_SUBMISSION'; submission: SubmissionEntry }
  | { type: 'REMOVE_SUBMISSION'; index: number }
  | { type: 'SET_HEALTH'; health: HealthResponse | null; error?: boolean }
  | { type: 'SET_RULES'; rules: RulesResponse }
  | { type: 'RESET' }

const emptyCaseInfo: CaseInfo = { clientName: '', caseType: 'renewal', lang: 'en' }

const initialCaseState: CaseState = {
  caseInfo: emptyCaseInfo,
  documents: [],
  records: [],
  evaluation: null,
  priorEvaluation: null,
  deadline: null,
  exemptionAnswers: [],
  submissions: [],
  step: 1,
  health: null,
  healthError: false,
  rules: null,
}

function caseReducer(state: CaseState, action: CaseAction): CaseState {
  switch (action.type) {
    case 'SET_STEP':
      return { ...state, step: action.step }
    case 'SET_LANG':
      return { ...state, caseInfo: { ...state.caseInfo, lang: action.lang } }
    case 'SET_CASE_INFO':
      return { ...state, caseInfo: action.caseInfo }
    case 'ADD_DOCUMENT':
      return { ...state, documents: [...state.documents, action.document] }
    case 'UPDATE_DOCUMENT':
      return {
        ...state,
        documents: state.documents.map((d) => (d.docId === action.docId ? { ...d, ...action.changes } : d)),
      }
    case 'REMOVE_DOCUMENT':
      return { ...state, documents: state.documents.filter((d) => d.docId !== action.docId) }
    case 'SET_RECORDS':
      return { ...state, records: action.records }
    case 'SET_EVALUATION':
      return {
        ...state,
        evaluation: action.evaluation,
        // Last non-null evaluation; survives a review-edit clear so Results can animate from it.
        priorEvaluation: state.evaluation ?? state.priorEvaluation,
        deadline: action.evaluation?.deadline ?? state.deadline,
      }
    case 'SET_DEADLINE':
      return { ...state, deadline: action.deadline }
    case 'SET_EXEMPTION_ANSWER':
      return {
        ...state,
        exemptionAnswers: [...state.exemptionAnswers.filter((a) => a.id !== action.answer.id), action.answer],
      }
    case 'ADD_SUBMISSION':
      return { ...state, submissions: [...state.submissions, action.submission] }
    case 'REMOVE_SUBMISSION':
      return { ...state, submissions: state.submissions.filter((_, i) => i !== action.index) }
    case 'SET_HEALTH':
      return { ...state, health: action.health, healthError: action.error ?? false }
    case 'SET_RULES':
      return { ...state, rules: action.rules }
    case 'RESET':
      // Keeps language, health, and rules; clears all case data.
      return {
        ...initialCaseState,
        caseInfo: { ...emptyCaseInfo, lang: state.caseInfo.lang },
        health: state.health,
        healthError: state.healthError,
        rules: state.rules,
      }
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
