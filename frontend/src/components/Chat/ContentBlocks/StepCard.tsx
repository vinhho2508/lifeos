import React from 'react'
import { Button, Disclosure } from '@heroui/react'

interface StepCardProps {
  icon: React.ReactNode
  title: string
  /** Secondary text beside the title (truncates). */
  detail?: string
  /** Right-aligned status adornment (spinner, check, ...). */
  status?: React.ReactNode
  children: React.ReactNode
}

/** Collapsed-by-default card used for agent steps (thinking, tool calls). */
const StepCard: React.FC<StepCardProps> = ({ icon, title, detail, status, children }) => (
  <Disclosure className="my-2 overflow-hidden rounded-lg border border-border bg-surface-secondary">
    <Disclosure.Heading>
      <Button
        slot="trigger"
        variant="ghost"
        fullWidth
        className="h-auto justify-start gap-2 rounded-none px-3 py-2 text-xs font-normal text-muted"
      >
        <Disclosure.Indicator className="size-3.5 shrink-0" />
        <span className="shrink-0">{icon}</span>
        <span className="shrink-0 font-medium text-foreground">{title}</span>
        {detail && <span className="min-w-0 truncate">{detail}</span>}
        {status && <span className="ml-auto shrink-0">{status}</span>}
      </Button>
    </Disclosure.Heading>
    <Disclosure.Content>
      <Disclosure.Body className="space-y-2 px-3 pb-3">{children}</Disclosure.Body>
    </Disclosure.Content>
  </Disclosure>
)

export default StepCard
