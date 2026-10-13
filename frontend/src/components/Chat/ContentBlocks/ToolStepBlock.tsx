import React from 'react'
import { CheckCircle2, Loader2, Wrench, XCircle } from 'lucide-react'
import { ToolCallBlock, ToolResultBlock } from '@/types/chat'
import StepCard from './StepCard'

const TOOL_LABELS: Record<string, string> = {
  search_documents: 'Search documents',
  list_documents: 'List documents',
  create_task: 'Create task',
  list_tasks: 'List tasks',
  update_task: 'Update task',
  generate_image: 'Generate image',
}

interface ToolStepBlockProps {
  call: ToolCallBlock
  result?: ToolResultBlock
}

/** One agent tool step: the call and (once it arrives) its result, collapsed by default. */
const ToolStepBlock: React.FC<ToolStepBlockProps> = ({ call, result }) => {
  const label = TOOL_LABELS[call.name] ?? call.name

  let status = <Loader2 className="size-3.5 animate-spin" aria-label="Running" />
  if (result?.status === 'ok') {
    status = <CheckCircle2 className="size-3.5 text-success" aria-label="Done" />
  }
  if (result?.status === 'error') {
    status = <XCircle className="size-3.5 text-danger" aria-label="Failed" />
  }

  return (
    <StepCard
      icon={<Wrench className="size-3.5" />}
      title={label}
      detail={result ? `· ${result.summary}` : '· running…'}
      status={status}
    >
      <div>
        <div className="mb-1 text-[11px] font-medium text-muted">Input</div>
        <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed">
          {JSON.stringify(call.input, null, 2)}
        </pre>
      </div>
      {result && (
        <div>
          <div className="mb-1 text-[11px] font-medium text-muted">Output</div>
          <pre className="max-h-64 overflow-auto whitespace-pre-wrap font-mono text-xs leading-relaxed">
            {typeof result.output === 'string'
              ? result.output
              : JSON.stringify(result.output, null, 2)}
          </pre>
        </div>
      )}
    </StepCard>
  )
}

export default ToolStepBlock
