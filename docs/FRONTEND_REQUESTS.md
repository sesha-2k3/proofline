# Frontend requests

## Requests
- 2026-10-24 (F1): shared/openapi.json has no paths or schemas yet, so `npm run gen:api` produces an empty schema.d.ts. Frontend needs B4 (routes with response_model) plus `make openapi` to finish the client.ts endpoint wrappers and the typed caseState fields (caseInfo, documents, records, evaluation, exemptionAnswers, submissions, health, rules).

## Changes
- 2026-10-24 (B2, additive): initial contract. Models: CaseInfo, StrField/NumField/BoolField/DateField/OrgTypeField, ErrorBody, EvidenceRecord, Flag, NoticeInfo, PipelineStage, MonthResult, GapItem, PossibleExemption, Deadline, HealthResponse, RulesResponse, SamplesResponse, DocumentResult, Validate/Evaluate/Packet/Timeline requests and responses, SubmissionEntry. Wire fields are camelCase (e.g. clientName, rfiReceivedDate, bestMonth, possibleExemptions). Schemas appear in shared/openapi.json once routes use them (B4).
