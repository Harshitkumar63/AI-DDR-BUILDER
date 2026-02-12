import { useState } from 'react';

/**
 * Collapsible panel showing validation warnings and conflict status.
 *
 * Props:
 *   warnings  - Array of warning strings / objects.
 *   conflicts - Array of conflict strings / objects.
 */
export default function ValidationPanel({ warnings = [], conflicts = [] }) {
  const [isOpen, setIsOpen] = useState(false);

  const totalIssues = warnings.length + conflicts.length;
  if (totalIssues === 0) return null;

  return (
    <div className="animate-fade-in border border-slate-200 rounded-2xl bg-white shadow-sm overflow-hidden">
      <button
        onClick={() => setIsOpen((prev) => !prev)}
        className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-slate-50"
      >
        <div className="flex items-center gap-3">
          <div className={`flex items-center justify-center w-8 h-8 rounded-lg
            ${conflicts.length > 0 ? 'bg-amber-100 text-amber-600' : 'bg-yellow-100 text-yellow-600'}`}>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.268 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <div>
            <span className="text-sm font-medium text-slate-700">
              Validation &amp; Conflicts
            </span>
            <span className="ml-2 inline-flex items-center justify-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700">
              {totalIssues}
            </span>
          </div>
        </div>
        <svg
          className={`w-5 h-5 text-slate-400 transform transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {isOpen && (
        <div className="border-t border-slate-100 px-6 py-4 space-y-4">
          {/* Conflicts */}
          {conflicts.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-amber-700 uppercase tracking-wider mb-2">
                Conflicts Detected
              </h4>
              <ul className="space-y-1.5">
                {conflicts.map((c, i) => (
                  <li key={i} className="flex gap-2 text-sm text-slate-700">
                    <span className="text-amber-500 mt-0.5 shrink-0">&#9679;</span>
                    <span>{typeof c === 'string' ? c : c.description || JSON.stringify(c)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Warnings */}
          {warnings.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-yellow-700 uppercase tracking-wider mb-2">
                Validation Warnings
              </h4>
              <ul className="space-y-1.5">
                {warnings.map((w, i) => (
                  <li key={i} className="flex gap-2 text-sm text-slate-600">
                    <span className="text-yellow-500 mt-0.5 shrink-0">&#9679;</span>
                    <span>{typeof w === 'string' ? w : w.detail || JSON.stringify(w)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
