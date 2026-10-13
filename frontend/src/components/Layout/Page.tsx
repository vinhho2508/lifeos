import React from 'react'

interface PageProps {
  title: string
  description?: string
  /** Optional actions rendered on the right of the header. */
  actions?: React.ReactNode
  /** Tailwind max-width class for the content column. */
  width?: string
  /** Fill the remaining height instead of scrolling (used by Chat). */
  fill?: boolean
  children: React.ReactNode
}

/** Shared page frame: header + width-constrained content column. */
const Page: React.FC<PageProps> = ({
  title,
  description,
  actions,
  width = 'max-w-4xl',
  fill = false,
  children,
}) => (
  <div
    className={`mx-auto flex w-full flex-1 flex-col px-4 py-5 md:px-8 md:py-8 ${width} ${
      fill ? 'min-h-0' : ''
    }`}
  >
    <div className="mb-5 flex items-start justify-between gap-4">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">{title}</h1>
        {description && <p className="mt-0.5 text-sm text-muted">{description}</p>}
      </div>
      {actions}
    </div>
    {fill ? <div className="flex min-h-0 flex-1 flex-col">{children}</div> : children}
  </div>
)

export default Page
