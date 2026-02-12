export default function Header() {
  return (
    <header className="w-full bg-white border-b border-slate-200">
      <div className="max-w-5xl mx-auto px-6 py-5 flex items-center gap-4">
        {/* Icon */}
        <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-blue-600 text-white font-bold text-lg shrink-0">
          D
        </div>

        <div>
          <h1 className="text-xl font-semibold text-slate-900 tracking-tight">
            AI DDR Builder
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Applied AI &middot; Detailed Diagnostic Report Generator
          </p>
        </div>
      </div>
    </header>
  );
}
