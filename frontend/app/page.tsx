import Link from 'next/link';
import { UserButton, SignedIn, SignedOut } from '@clerk/nextjs';
import { currentUser } from '@clerk/nextjs/server';
import { redirect } from 'next/navigation';

export default async function Home() {
  const user = await currentUser();
  if (user) redirect('/dashboard');

  return (
    <main className="min-h-screen bg-white">
      {/* Navigation */}
      <nav className="bg-brown-600 text-white sticky top-0 z-50 shadow-lg">
        <div className="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center">
          <Link href="/" className="text-2xl font-display font-bold tracking-tight">
            Kansi AI
          </Link>
          <div className="flex items-center gap-4">
            <SignedIn>
              <Link href="/dashboard" className="btn-primary text-sm py-2 px-5">
                Dashboard
              </Link>
              <UserButton />
            </SignedIn>
            <SignedOut>
              <Link href="/sign-in" className="text-sm font-medium text-brown-100 hover:text-white transition-colors">
                Sign in
              </Link>
              <Link href="/sign-up" className="btn-primary text-sm py-2 px-5">
                Get started
              </Link>
            </SignedOut>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="py-24 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <span className="inline-block bg-brown-50 text-brown-600 text-xs font-semibold tracking-widest uppercase px-4 py-2 rounded-full mb-6 border border-brown-200">
            Mental health screening
          </span>
          <h1 className="text-5xl md:text-6xl font-display font-bold text-brown-800 leading-tight mb-6">
            Your Safe Space for<br />
            <span className="text-brown-500">Emotional Clarity</span>
          </h1>
          <p className="text-xl text-brown-400 mb-12 max-w-2xl mx-auto leading-relaxed">
            AI-powered screening that listens without judgment. Private, instant insights — crafted with care.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/sign-up" className="btn-primary text-lg py-4 px-10">
              Begin your journey
            </Link>
            <Link href="/sign-in" className="btn-outline text-lg py-4 px-10">
              Sign in
            </Link>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-20 px-4 bg-brown-50">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-3xl font-display font-bold text-brown-800 text-center mb-12">How it works</h2>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              { step: '01', title: 'Share how you feel', body: 'Write freely in a private, judgment-free space. No personal details required.' },
              { step: '02', title: 'AI analysis', body: 'Our trained model screens for emotional distress indicators in seconds.' },
              { step: '03', title: 'Actionable insights', body: 'Receive a clear result with confidence score and next-step suggestions.' },
            ].map(({ step, title, body }) => (
              <div key={step} className="card text-center">
                <div className="text-4xl font-display font-bold text-brown-200 mb-3">{step}</div>
                <h3 className="text-lg font-display font-semibold text-brown-700 mb-2">{title}</h3>
                <p className="text-brown-400 text-sm leading-relaxed">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-4 border-t border-brown-100">
        <div className="max-w-6xl mx-auto text-center text-brown-300 text-sm">
          © {new Date().getFullYear()} Kansi AI — Screening tool only. Not a clinical diagnosis.
        </div>
      </footer>
    </main>
  );
}
