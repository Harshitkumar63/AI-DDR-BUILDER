/**
 * Renders the DDR report text with clean formatting.
 * Splits on known section headings and renders each as a styled block.
 */
export default function DDRDisplay({ report }) {
  if (!report) return null;

  const sections = parseSections(report);

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-slate-900">Generated Report</h2>
        <button
          onClick={() => downloadReport(report)}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium
                     text-blue-600 bg-blue-50 rounded-xl hover:bg-blue-100"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Download TXT
        </button>
      </div>

      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden divide-y divide-slate-100">
        {sections.map((section, idx) => (
          <div key={idx} className="px-6 py-5">
            {section.heading && (
              <h3 className="text-sm font-semibold text-blue-600 uppercase tracking-wider mb-3">
                {section.heading}
              </h3>
            )}
            <div className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
              {section.body}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Helpers ───────────────────────────────────────────────── */

function parseSections(text) {
  // Known DDR headings — match lines that are ALL-CAPS headings
  const headingPattern = /^([A-Z][A-Z /\-()&]{4,})$/;
  const lines = text.split('\n');
  const sections = [];
  let current = { heading: '', body: '' };

  for (const line of lines) {
    const trimmed = line.trim();

    // Skip separator lines
    if (/^[=\-]{5,}$/.test(trimmed)) continue;

    // Skip meta lines (Generated, Source, etc.) — they're in the header
    if (trimmed.startsWith('Generated :') || trimmed.startsWith('Source ')) continue;
    if (trimmed === 'DETAILED DIAGNOSTIC REPORT (DDR)') continue;
    if (trimmed === 'END OF REPORT') continue;

    // Check if this line is a heading
    if (headingPattern.test(trimmed) && trimmed.length > 4) {
      if (current.heading || current.body.trim()) {
        sections.push({ ...current, body: current.body.trim() });
      }
      current = { heading: trimmed, body: '' };
    } else {
      current.body += line + '\n';
    }
  }

  // Push last section
  if (current.heading || current.body.trim()) {
    sections.push({ ...current, body: current.body.trim() });
  }

  return sections.filter((s) => s.body);
}

function downloadReport(text) {
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `DDR_Report_${new Date().toISOString().slice(0, 10)}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
