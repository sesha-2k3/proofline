export const en = {
  appName: 'Proofline',
  demoMode: 'Demo mode',
  languageLabel: 'Language',
  stepsLabel: 'Case steps',
  stepCase: 'Case',
  stepDocuments: 'Documents',
  stepReview: 'Review',
  stepResults: 'Results',
  stepPacket: 'Packet',
  landingTitle: 'Help your client show one qualifying month',
  landingIntro:
    "Proofline helps you gather a client's MassHealth notice and proof of work, volunteering, or school, and checks what each document says. It finds the strongest single month and builds a packet and a record of what you sent.",
  startCase: 'Start a case',
  loadSample: 'Load sample case (Jorge)',
  sampleNote: 'The sample case uses made-up documents.',
  caseTitle: 'New case',
  sampleCaseTitle: 'Sample case: Jorge Ramos',
  comingSoon: 'This step is not ready yet.',
}

export type MessageKey = keyof typeof en
export type Messages = Record<MessageKey, string>
