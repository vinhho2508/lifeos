import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'

interface TextBlockProps {
  text: string
}

const TextBlock: React.FC<TextBlockProps> = ({ text }) => {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        code({ className, children }) {
          const match = /language-(\w+)/.exec(className || '')
          const isBlock = !!match || String(children).includes('\n')
          if (!isBlock) {
            return (
              <code className="rounded bg-surface-tertiary px-1 py-0.5 font-mono text-[0.85em]">
                {children}
              </code>
            )
          }
          const language = match ? match[1] : 'text'
          return (
            <SyntaxHighlighter
              style={oneDark}
              language={language}
              PreTag="div"
              className="my-2 rounded-lg text-sm"
            >
              {String(children).replace(/\n$/, '')}
            </SyntaxHighlighter>
          )
        },
        p({ children }) {
          return <p className="mb-2 last:mb-0">{children}</p>
        },
        ul({ children }) {
          return <ul className="list-disc pl-5 mb-2">{children}</ul>
        },
        ol({ children }) {
          return <ol className="list-decimal pl-5 mb-2">{children}</ol>
        },
        li({ children }) {
          return <li className="mb-1">{children}</li>
        },
        h1({ children }) {
          return <h1 className="mb-2 mt-4 text-xl font-semibold">{children}</h1>
        },
        h2({ children }) {
          return <h2 className="mb-2 mt-4 text-lg font-semibold">{children}</h2>
        },
        h3({ children }) {
          return <h3 className="mb-1 mt-3 text-base font-semibold">{children}</h3>
        },
        a({ href, children }) {
          return (
            <a
              href={href}
              className="text-link underline underline-offset-2 hover:opacity-80"
              target="_blank"
              rel="noreferrer"
            >
              {children}
            </a>
          )
        },
        blockquote({ children }) {
          return (
            <blockquote className="my-2 border-l-2 border-border pl-4 italic text-muted">
              {children}
            </blockquote>
          )
        },
        table({ children }) {
          return (
            <div className="overflow-x-auto my-2">
              <table className="min-w-full border-collapse border border-border text-sm">
                {children}
              </table>
            </div>
          )
        },
        thead({ children }) {
          return <thead className="bg-surface-secondary">{children}</thead>
        },
        th({ children }) {
          return (
            <th className="border border-border px-3 py-2 text-left font-semibold">{children}</th>
          )
        },
        td({ children }) {
          return <td className="border border-border px-3 py-2">{children}</td>
        },
      }}
    >
      {text}
    </ReactMarkdown>
  )
}

export default TextBlock
