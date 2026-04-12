import { SignIn } from '@clerk/nextjs';

export default function SignInPage() {
  return (
    <main className="min-h-screen bg-white flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-display font-bold text-brown-700">Kansi AI</h1>
          <p className="text-brown-400 mt-1 text-sm">Sign in to continue your journey</p>
        </div>
        <SignIn
          appearance={{
            elements: {
              card: 'shadow-none border border-brown-100 rounded-3xl',
              headerTitle: 'font-display text-brown-800',
              formButtonPrimary:
                'bg-brown-600 hover:bg-brown-700 text-white font-semibold rounded-xl shadow-none',
              footerActionLink: 'text-brown-500 hover:text-brown-700',
            },
          }}
        />
      </div>
    </main>
  );
}
