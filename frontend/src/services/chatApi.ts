import api from './api'
import type { Conversation, Message } from '@/types/chat'

export async function listConversations(): Promise<Conversation[]> {
  return (await api.get<Conversation[]>('/chat/conversations')).data
}

export async function createConversation(): Promise<Conversation> {
  return (await api.post<Conversation>('/chat/conversations')).data
}

export async function renameConversation(id: string, title: string): Promise<Conversation> {
  return (await api.patch<Conversation>(`/chat/conversations/${id}`, { title })).data
}

export async function deleteConversation(id: string): Promise<void> {
  await api.delete(`/chat/conversations/${id}`)
}

const PAGE_SIZE = 200

function toMessage(m: Record<string, unknown>): Message {
  return {
    id: m.id as string,
    sender: m.sender as Message['sender'],
    text: m.text as string,
    content: (m.content as Message['content']) || [],
    timestamp: m.timestamp as string,
  }
}

/** The whole conversation, oldest first (fetched newest-page-first until exhausted). */
export async function getConversationMessages(id: string): Promise<Message[]> {
  let all: Message[] = []
  let before: string | undefined
  for (;;) {
    const { data } = await api.get<Record<string, unknown>[]>(
      `/chat/conversations/${id}/messages`,
      { params: { limit: PAGE_SIZE, before } },
    )
    const page = data.map(toMessage)
    all = [...page, ...all]
    if (page.length < PAGE_SIZE) return all
    before = page[0].timestamp
  }
}
