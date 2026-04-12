"use client";

import { useUser, UserButton, SignedIn, SignedOut, RedirectToSignIn } from '@clerk/nextjs';
import Link from 'next/link';

export default function Profile() {
  const { user } = useUser();

  const initials =
    (user?.firstName?.[0] ?? '') + (user?.lastName?.[0] ?? '') ||
    user?.primaryEmailAddress?.emailAddress?.[0]?.toUpperCase() ||
    '?';

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
                <Link href="/dashboard" className="text-sm font-medium text-brown-100 hover:text-white transition-colors">
                  Dashboard
                </Link>
                <UserButton />
              </div>
            </div>
          </nav>

          <div className="max-w-2xl mx-auto px-4 py-12">
            <div className="card text-center">
              {/* Avatar */}
              <div className="w-28 h-28 bg-gradient-to-br from-brown-400 to-brown-600 rounded-full mx-auto mb-6 flex items-center justify-center text-3xl font-bold text-white shadow-xl">
                {initials}
              </div>

              <h1 className="text-3xl font-display font-bold text-brown-800 mb-1">
                {user?.fullName || 'Your Profile'}
              </h1>
              <p className="text-brown-500 mb-8">
                {user?.primaryEmailAddress?.emailAddress}
              </p>

              <div className="grid grid-cols-2 gap-4 max-w-xs mx-auto">
                <Link href="/dashboard" className="btn-primary text-center">
                  Dashboard
                </Link>
                <Link href="/history" className="btn-outline text-center">
                  History
                </Link>
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
