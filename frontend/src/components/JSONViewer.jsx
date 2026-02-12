import { useState } from 'react';

/**
 * Collapsible JSON viewer for the extracted structured data.
 *
 * Props:
 *   data  - The object to render as formatted JSON.
 *   title - Section title.
 */
export default function JSONViewer({ data, title = 'Extracted Data' }) {
  const [isOpen, setIsOpen] = useState(false);

  if (!data) return null;

  return (
    <div className="animate-fade-in border border-slate-200 rounded-2xl bg-white shadow-sm overflow-hidden">
      <button
        onClick={() => setIsOpen((prev) => !prev)}
        className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-slate-50"
      >
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-slate-100 text-slate-500">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
            </svg>
          </div>
          <span className="text-sm font-medium text-slate-700">{title}</span>
        </div>
        <svg
          className={`w-5 h-5 text-slate-400 transform transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className="border-t border-slate-100 px-6 py-4 bg-slate-50">
          <pre className="text-xs text-slate-600 leading-relaxed overflow-x-auto max-h-96 overflow-y-auto">
            {JSON.stringify(data, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
