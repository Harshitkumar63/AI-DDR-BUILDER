import { useState, useCallback } from 'react';
import FileUpload from '../components/FileUpload';
import DDRDisplay from '../components/DDRDisplay';
import JSONViewer from '../components/JSONViewer';
import ValidationPanel from '../components/ValidationPanel';
import { generateDDR } from '../services/api';

export default function Home() {
  // File state
  const [inspectionFile, setInspectionFile] = useState(null);
  const [thermalFile, setThermalFile] = useState(null);

  // Pipeline state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Result state
  const [report, setReport] = useState(null);
  const [extractedData, setExtractedData] = useState(null);
  const [conflicts, setConflicts] = useState([]);
  const [warnings, setWarnings] = useState([]);

  const canGenerate = inspectionFile && thermalFile && !loading;

  const handleGenerate = useCallback(async () => {
    if (!inspectionFile || !thermalFile) return;

    setLoading(true);
    setError(null);
    setReport(null);
    setExtractedData(null);
    setConflicts([]);
    setWarnings([]);

    try {
      const data = await generateDDR(inspectionFile, thermalFile);

      setReport(data.ddr_report || '');
      setExtractedData(data.extracted_data || null);
      setConflicts(data.conflicts || []);
      setWarnings(data.validation_warnings || []);
    } catch (err) {
      const message =
        err.response?.data?.detail ||
        err.response?.data?.error ||
        err.message ||
        'Something went wrong. Please try again.';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [inspectionFile, thermalFile]);

  const handleReset = useCallback(() => {
    setInspectionFile(null);
    setThermalFile(null);
    setReport(null);
    setExtractedData(null);
    setConflicts([]);
    setWarnings([]);
    setError(null);
  }, []);

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 space-y-8">

      {/* ── Upload Section ────────────────────────────────── */}
      <section className="bg-white border border-slate-200 rounded-2xl shadow-sm p-6">
        <h2 className="text-base font-semibold text-slate-900 mb-1">
          Upload Documents
        </h2>
        <p className="text-sm text-slate-500 mb-5">
          Upload both the Inspection Report and Thermal Report to generate a DDR.
        </p>

        <div className="flex flex-col sm:flex-row gap-4">
          <FileUpload
            label="Inspection Report"
            file={inspectionFile}
            onFileChange={setInspectionFile}
            disabled={loading}
          />
          <FileUpload
            label="Thermal Report"
            file={thermalFile}
            onFileChange={setThermalFile}
            disabled={loading}
          />
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3 mt-6">
          <button
            onClick={handleGenerate}
            disabled={!canGenerate}
            className={`
              inline-flex items-center gap-2.5 px-6 py-2.5 rounded-xl text-sm font-medium
              transition-all duration-150
              ${canGenerate
                ? 'bg-blue-600 text-white hover:bg-blue-700 shadow-sm shadow-blue-200'
                : 'bg-slate-100 text-slate-400 cursor-not-allowed'
              }
            `}
          >
            {loading && <Spinner />}
            {loading ? 'Generating Report...' : 'Generate DDR'}
          </button>

          {report && (
            <button
              onClick={handleReset}
              className="px-4 py-2.5 rounded-xl text-sm font-medium text-slate-600
                         bg-slate-100 hover:bg-slate-200"
            >
              Reset
            </button>
          )}
        </div>
      </section>

      {/* ── Loading State ─────────────────────────────────── */}
      {loading && (
        <div className="animate-fade-in flex flex-col items-center gap-3 py-12">
          <div className="w-10 h-10 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
          <p className="text-sm text-slate-500">
            Analyzing documents and generating report...
          </p>
          <p className="text-xs text-slate-400">This may take up to a minute.</p>
        </div>
      )}

      {/* ── Error Toast ───────────────────────────────────── */}
      {error && (
        <div className="animate-fade-in flex items-start gap-3 bg-red-50 border border-red-200 rounded-2xl px-5 py-4">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-red-100 text-red-500 shrink-0 mt-0.5">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-red-800">Generation Failed</p>
            <p className="text-sm text-red-600 mt-0.5">{error}</p>
          </div>
          <button
            onClick={() => setError(null)}
            className="ml-auto p-1 rounded-lg hover:bg-red-100 text-red-400 hover:text-red-600 shrink-0"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* ── DDR Report ────────────────────────────────────── */}
      {report && !loading && (
        <section>
          <DDRDisplay report={report} />
        </section>
      )}

      {/* ── Advanced Section ──────────────────────────────── */}
      {report && !loading && (
        <section className="space-y-3">
          <h2 className="text-base font-semibold text-slate-900">Advanced Details</h2>

          <ValidationPanel warnings={warnings} conflicts={conflicts} />
          <JSONViewer data={extractedData} title="Extracted Structured Data" />
        </section>
      )}
    </div>
  );
}

/* ── Inline spinner ───────────────────────────────────────── */
function Spinner() {
  return (
    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  );
}
