"use client";

import { useUser, useAuth, UserButton, SignedIn, SignedOut, RedirectToSignIn } from '@clerk/nextjs';
import { useState, useEffect } from 'react';
import Link from 'next/link';

interface AnalysisResult {
  prediction: string;
  confidence: number;
  model: string;
  disclaimer: string;
}

interface HistoryItem {
  id: number;
  input_text: string;
  prediction: string;
  confidence: number;
  created_at: string;
}

export default function Dashboard() {
  const { user } = useUser();
  const { getToken } = useAuth();
  const [analysisHistory, setAnalysisHistory] = useState<HistoryItem[]>([]);
  const [text, setText] = useState('');
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const token = await getToken();
        const res = await fetch('/api/history?limit=5', {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setAnalysisHistory(data.history || []);
        }
      } catch {
        // History is optional — don't block the page
      }
    };
    if (user) fetchHistory();
  }, [user, getToken]);

  const handleAnalyze = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const token = await getToken();
      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ text }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.error || 'Analysis failed. Please try again.');
      } else {
        setResult(data);
        // Refresh history
        const histRes = await fetch('/api/history?limit=5', {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (histRes.ok) {
          const histData = await histRes.json();
          setAnalysisHistory(histData.history || []);
        }
      }
    } catch {
      setError('Connection error. Please check that the server is running.');
    } finally {
      setLoading(false);
    }
  };

  const isDepressive = result?.prediction === 'depressive';

  return (
    <>
      <SignedIn>
        <main className="min-h-screen bg-white">
          {/* Navigation */}
          <nav className="bg-brown-600 text-white sticky top-0 z-50 shadow-lg">
            <div className="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center">
              <Link href="/" className="text-2xl font-display font-bold tracking-tight">
                Kansi AI
              </Link>
              <div className="flex items-center gap-6">
                <Link href="/history" className="text-sm font-medium text-brown-100 hover:text-white transition-colors">
                  History
                </Link>
                <Link href="/profile" className="text-sm font-medium text-brown-100 hover:text-white transition-colors">
                  Profile
                </Link>
                <UserButton />
              </div>
            </div>
          </nav>

          <div className="max-w-6xl mx-auto px-4 py-10">
            <div className="grid md:grid-cols-3 gap-8">
              {/* Main analysis panel */}
              <div className="md:col-span-2 space-y-6">
                <div className="card">
                  <h1 className="text-3xl font-display font-bold text-brown-800 mb-2">
                    Welcome back{user?.firstName ? `, ${user.firstName}` : ''}
                  </h1>
                  <p className="text-brown-500 mb-6">Share what's on your mind for a private, judgment-free screening.</p>
                  <textarea
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="Describe how you've been feeling lately…"
                    className="w-full p-5 rounded-2xl border-2 border-brown-100 focus:border-brown-400 focus:outline-none bg-white resize-vertical min-h-[160px] text-base text-brown-900 placeholder-brown-300 transition-colors"
                  />
                  {error && (
                    <p className="mt-3 text-red-600 text-sm bg-red-50 border border-red-200 rounded-xl px-4 py-3">{error}</p>
                  )}
                  <button
                    onClick={handleAnalyze}
                    disabled={loading || !text.trim()}
                    className="btn-primary mt-5 w-full md:w-auto disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
                  >
                    {loading ? (
                      <span className="flex items-center gap-2">
                        <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/>
                        </svg>
                        Analyzing…
                      </span>
                    ) : 'Analyze'}
                  </button>
                </div>

                {/* Result card */}
                {result && (
                  <div className={`card border-l-4 ${isDepressive ? 'border-amber-500 bg-amber-50' : 'border-green-500 bg-green-50'}`}>
                    <div className="flex items-start gap-4">
                      <div className={`w-12 h-12 rounded-full flex items-center justify-center text-2xl flex-shrink-0 ${isDepressive ? 'bg-amber-100' : 'bg-green-100'}`}>
                        {isDepressive ? '⚠️' : '✓'}
                      </div>
                      <div>
                        <h2 className="text-xl font-display font-bold text-brown-800 mb-1">
                          {isDepressive ? 'Indicators Detected' : 'Low Risk'}
                        </h2>
                        <p className="text-brown-600 mb-3">
                          Confidence: <strong>{result.confidence}%</strong> &nbsp;·&nbsp; Model: {result.model}
                        </p>
                        <p className="text-sm text-brown-500 italic">{result.disclaimer}</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Sidebar */}
              <div className="space-y-6">
                <div className="card">
                  <h3 className="text-lg font-display font-semibold text-brown-700 mb-4">Recent Analyses</h3>
                  {analysisHistory.length === 0 ? (
                    <p className="text-brown-400 text-sm">No analyses yet. Share something above to get started.</p>
                  ) : (
                    <ul className="space-y-3">
                      {analysisHistory.map((item) => (
                        <li key={item.id} className="p-3 bg-brown-50 rounded-xl border border-brown-100">
                          <p className="text-sm text-brown-700 truncate">{item.input_text}</p>
                          <p className="text-xs text-brown-400 mt-1">
                            {item.prediction} · {item.confidence}%
                          </p>
                        </li>
                      ))}
                    </ul>
                  )}
                  {analysisHistory.length > 0 && (
                    <Link href="/history" className="block mt-4 text-sm text-brown-500 hover:text-brown-700 font-medium text-center">
                      View all →
                    </Link>
                  )}
                </div>
              </div>
            </div>
          </div>
        </main>
      </SignedIn>
      <SignedOut>
        <RedirectToSignIn />
      </SignedOut>
    </>
  );
}
