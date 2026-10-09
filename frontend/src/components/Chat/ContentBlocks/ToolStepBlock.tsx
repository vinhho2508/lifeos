import React, { useState } from 'react'
import { CheckCircle2, ChevronDown, ChevronRight, Loader2, Wrench, XCircle } from 'lucide-react'
import { ToolCallBlock, ToolResultBlock } from '@/types/chat'

const TOOL_LABELS: Record<string, string> = {
  search_documents: 'Search documents',
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
  const [expanded, setExpanded] = useState(false)
  const label = TOOL_LABELS[call.name] ?? call.name

  let icon = <Loader2 className="w-3.5 h-3.5 animate-spin" />
  if (result?.status === 'ok') icon = <CheckCircle2 className="w-3.5 h-3.5 text-green-600" />
  if (result?.status === 'error') icon = <XCircle className="w-3.5 h-3.5 text-destructive" />

  return (
    <div className="my-2 rounded-lg border border-muted bg-muted/40 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 w-full px-3 py-2 text-left text-xs text-muted-foreground hover:bg-muted/60 transition-colors"
      >
        {expanded ? (
          <ChevronDown className="w-3.5 h-3.5 shrink-0" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 shrink-0" />
        )}
        <Wrench className="w-3.5 h-3.5 shrink-0" />
        <span className="font-medium">{label}</span>
        <span className="truncate">{result ? `· ${result.summary}` : '· running…'}</span>
        <span className="ml-auto shrink-0">{icon}</span>
      </button>
      {expanded && (
        <div className="px-3 pb-3 space-y-2">
          <div>
            <div className="text-[11px] font-medium text-muted-foreground mb-1">Input</div>
            <pre className="text-xs whitespace-pre-wrap font-mono leading-relaxed">
              {JSON.stringify(call.input, null, 2)}
            </pre>
          </div>
          {result && (
            <div>
              <div className="text-[11px] font-medium text-muted-foreground mb-1">Output</div>
              <pre className="text-xs whitespace-pre-wrap font-mono leading-relaxed max-h-64 overflow-auto">
                {typeof result.output === 'string'
                  ? result.output
                  : JSON.stringify(result.output, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default ToolStepBlock
