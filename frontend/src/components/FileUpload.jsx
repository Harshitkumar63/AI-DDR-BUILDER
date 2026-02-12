import { useCallback, useRef, useState } from 'react';

/**
 * A single file-upload card with drag-and-drop support.
 *
 * Props:
 *   label       - Label text (e.g. "Inspection Report")
 *   accept      - Accepted file types string (e.g. ".pdf,.txt")
 *   file        - Currently selected File or null
 *   onFileChange - Callback: (file: File | null) => void
 *   disabled    - Whether the upload is disabled
 */
export default function FileUpload({ label, accept = '.pdf,.txt', file, onFileChange, disabled = false }) {
  const inputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFile = useCallback(
    (f) => {
      if (f && onFileChange) onFileChange(f);
    },
    [onFileChange],
  );

  const onDrop = useCallback(
    (e) => {
      e.preventDefault();
      setIsDragging(false);
      if (disabled) return;
      const f = e.dataTransfer.files?.[0];
      if (f) handleFile(f);
    },
    [disabled, handleFile],
  );

  const onDragOver = useCallback(
    (e) => {
      e.preventDefault();
      if (!disabled) setIsDragging(true);
    },
    [disabled],
  );

  const onDragLeave = useCallback(() => setIsDragging(false), []);

  const onInputChange = useCallback(
    (e) => {
      const f = e.target.files?.[0];
      if (f) handleFile(f);
    },
    [handleFile],
  );

  const removeFile = useCallback(
    (e) => {
      e.stopPropagation();
      if (onFileChange) onFileChange(null);
      if (inputRef.current) inputRef.current.value = '';
    },
    [onFileChange],
  );

  const formatSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1048576).toFixed(1)} MB`;
  };

  return (
    <div className="flex-1 min-w-0">
      <p className="text-sm font-medium text-slate-700 mb-2">{label}</p>

      <div
        onClick={() => !disabled && inputRef.current?.click()}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        className={`
          relative flex flex-col items-center justify-center
          border-2 border-dashed rounded-2xl px-6 py-8
          cursor-pointer select-none
          ${disabled ? 'opacity-50 cursor-not-allowed bg-slate-50' : ''}
          ${isDragging
            ? 'border-blue-400 bg-blue-50'
            : file
              ? 'border-green-300 bg-green-50/40'
              : 'border-slate-300 bg-slate-50/50 hover:border-blue-300 hover:bg-blue-50/30'
          }
        `}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          onChange={onInputChange}
          disabled={disabled}
          className="hidden"
        />

        {file ? (
          /* ── File selected ── */
          <div className="flex items-center gap-3 w-full">
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-green-100 text-green-600 shrink-0">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-slate-800 truncate">{file.name}</p>
              <p className="text-xs text-slate-500">{formatSize(file.size)}</p>
            </div>
            {!disabled && (
              <button
                onClick={removeFile}
                className="p-1 rounded-lg hover:bg-red-100 text-slate-400 hover:text-red-500"
                title="Remove file"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
        ) : (
          /* ── Empty state ── */
          <>
            <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-slate-100 text-slate-400 mb-3">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <p className="text-sm text-slate-600 text-center">
              <span className="font-medium text-blue-600">Click to upload</span>{' '}
              or drag and drop
            </p>
            <p className="text-xs text-slate-400 mt-1">PDF or TXT</p>
          </>
        )}
      </div>
    </div>
  );
}
