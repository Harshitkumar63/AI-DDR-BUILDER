import Header from './components/Header';
import Home from './pages/Home';

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50">
      <Header />
      <main>
        <Home />
      </main>

      {/* Footer */}
      <footer className="max-w-5xl mx-auto px-6 py-6 text-center">
        <p className="text-xs text-slate-400">
          AI DDR Builder &middot; Applied AI Diagnostic Report Generator
        </p>
      </footer>
    </div>
  );
}
