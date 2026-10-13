import React, { useEffect, useState } from 'react'
import { Check, MessageSquarePlus, Pencil, Trash2, X } from 'lucide-react'
import type { Conversation } from '@/types/chat'
import { deleteConversation, listConversations, renameConversation } from '@/services/chatApi'

interface Props {
  activeId?: string
  /** Bump to refetch (e.g. after a turn updated a title). */
  refreshKey: number
  onSelect: (id: string) => void
  onNew: () => void
  /** Called after the active conversation was deleted. */
  onDeletedActive: () => void
}

const iconBtn =
  'flex size-6 items-center justify-center rounded text-muted hover:bg-surface-secondary hover:text-foreground'

const ConversationList: React.FC<Props> = ({
  activeId,
  refreshKey,
  onSelect,
  onNew,
  onDeletedActive,
}) => {
  const [items, setItems] = useState<Conversation[]>([])
  const [editingId, setEditingId] = useState<string | null>(null)
  const [draft, setDraft] = useState('')
  const [confirmId, setConfirmId] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    listConversations()
      .then((list) => {
        if (!cancelled) setItems(list)
      })
      .catch((err) => console.error('Failed to load conversations:', err))
    return () => {
      cancelled = true
    }
  }, [refreshKey])

  const commitRename = async (id: string) => {
    const title = draft.trim()
    setEditingId(null)
    if (!title) return
    try {
      const updated = await renameConversation(id, title)
      setItems((prev) => prev.map((c) => (c.id === id ? updated : c)))
    } catch (err) {
      console.error('Rename failed:', err)
    }
  }

  const remove = async (id: string) => {
    setConfirmId(null)
    try {
      await deleteConversation(id)
      setItems((prev) => prev.filter((c) => c.id !== id))
      if (id === activeId) onDeletedActive()
    } catch (err) {
      console.error('Delete failed:', err)
    }
  }

  return (
    <div className="flex min-h-0 flex-col gap-2">
      <button
        type="button"
        onClick={onNew}
        className="flex items-center gap-2 rounded-md border border-border px-2.5 py-1.5 text-sm font-medium hover:bg-surface-secondary"
      >
        <MessageSquarePlus className="size-4" />
        New chat
      </button>
      <ul className="min-h-0 flex-1 space-y-0.5 overflow-y-auto" aria-label="Conversations">
        {items.map((c) => {
          const active = c.id === activeId
          return (
            <li key={c.id}>
              {editingId === c.id ? (
                <div className="flex items-center gap-1 px-1">
                  <input
                    autoFocus
                    aria-label="Conversation title"
                    value={draft}
                    maxLength={200}
                    onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') commitRename(c.id)
                      if (e.key === 'Escape') setEditingId(null)
                    }}
                    className="min-w-0 flex-1 rounded border border-border bg-surface px-1.5 py-1 text-sm"
                  />
                  <button
                    type="button"
                    aria-label="Save"
                    className={iconBtn}
                    onClick={() => commitRename(c.id)}
                  >
                    <Check className="size-3.5" />
                  </button>
                </div>
              ) : (
                <div
                  className={`group flex items-center gap-1 rounded-md pr-1 ${
                    active
                      ? 'bg-accent-soft text-accent-soft-foreground'
                      : 'hover:bg-surface-secondary'
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => onSelect(c.id)}
                    aria-current={active ? 'true' : undefined}
                    className="min-w-0 flex-1 truncate px-2.5 py-1.5 text-left text-sm"
                    title={c.title}
                  >
                    {c.title}
                  </button>
                  {confirmId === c.id ? (
                    <>
                      <button
                        type="button"
                        aria-label="Confirm delete"
                        className={iconBtn}
                        onClick={() => remove(c.id)}
                      >
                        <Check className="size-3.5" />
                      </button>
                      <button
                        type="button"
                        aria-label="Cancel delete"
                        className={iconBtn}
                        onClick={() => setConfirmId(null)}
                      >
                        <X className="size-3.5" />
                      </button>
                    </>
                  ) : (
                    <span className="hidden gap-0.5 group-focus-within:flex group-hover:flex">
                      <button
                        type="button"
                        aria-label="Rename"
                        className={iconBtn}
                        onClick={() => {
                          setDraft(c.title)
                          setEditingId(c.id)
                        }}
                      >
                        <Pencil className="size-3.5" />
                      </button>
                      <button
                        type="button"
                        aria-label="Delete"
                        className={iconBtn}
                        onClick={() => setConfirmId(c.id)}
                      >
                        <Trash2 className="size-3.5" />
                      </button>
                    </span>
                  )}
                </div>
              )}
            </li>
          )
        })}
        {items.length === 0 && <li className="px-2.5 py-1.5 text-sm text-muted">No chats yet</li>}
      </ul>
    </div>
  )
}

export default ConversationList
