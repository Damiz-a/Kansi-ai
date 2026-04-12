"use client";

import { useAuth, UserButton, SignedIn, SignedOut, RedirectToSignIn } from '@clerk/nextjs';
import { useState, useEffect } from 'react';
import Link from 'next/link';

interface HistoryItem {
  id: number;
  input_text: string;
  prediction: string;
  confidence: number;
  model_used: string;
  created_at: string;
}

export default function History() {
  const { getToken } = useAuth();
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const token = await getToken();
        const res = await fetch('/api/history?limit=100', {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setHistory(data.history || []);
        } else {
          setError('Could not load history.');
        }
      } catch {
        setError('Connection error.');
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, [getToken]);

  return (
    <>
      <SignedIn>
        <main className="min-h-screen bg-white">
          <nav className="bg-brown-600 text-white sticky top-0 z-50 shadow-lg">
            <div className="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center">
              <Link href="/" className="text-2xl font-display font-bold tracking-tight">
                Kansi AI
              </Link>
              <div className="flex items-center gap-6">
                <Link href="/dashboard" className="text-sm font-medium text-brown-100 hover:text-white transition-colors">
                  Dashboard
                </Link>
                <Link href="/profile" className="text-sm font-medium text-brown-100 hover:text-white transition-colors">
                  Profile
                </Link>
                <UserButton />
              </div>
            </div>
          </nav>

          <div className="max-w-4xl mx-auto px-4 py-10">
            <h1 className="text-3xl font-display font-bold text-brown-800 mb-8">Analysis History</h1>

            {loading && (
              <div className="text-center py-20 text-brown-400">Loading…</div>
            )}
            {error && (
              <p className="text-red-600 bg-red-50 border border-red-200 rounded-xl px-4 py-3">{error}</p>
            )}
            {!loading && history.length === 0 && !error && (
              <div className="card text-center py-16">
                <p className="text-brown-400 mb-4">No analyses yet.</p>
                <Link href="/dashboard" className="btn-primary">Run your first analysis</Link>
              </div>
            )}

            {!loading && history.length > 0 && (
              <div className="space-y-4">
                {history.map((item) => {
                  const isDepressive = item.prediction.toLowerCase().includes('depressive');
                  return (
                    <div key={item.id} className={`card border-l-4 ${isDepressive ? 'border-amber-400' : 'border-green-400'}`}>
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <p className="text-brown-700 text-sm line-clamp-2">{item.input_text}</p>
                          <div className="flex flex-wrap gap-3 mt-2">
                            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${isDepressive ? 'bg-amber-100 text-amber-700' : 'bg-green-100 text-green-700'}`}>
                              {item.prediction}
                            </span>
                            <span className="text-xs text-brown-400">{item.confidence}% confidence</span>
                            <span className="text-xs text-brown-300">{item.model_used}</span>
                          </div>
                        </div>
                        <time className="text-xs text-brown-300 flex-shrink-0 mt-0.5">
                          {new Date(item.created_at).toLocaleDateString()}
                        </time>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </main>
      </SignedIn>
      <SignedOut>
        <RedirectToSignIn />
      </SignedOut>
    </>
  );
}
