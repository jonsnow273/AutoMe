import { useAuth } from '../hooks/useAuth'

// Placeholder — will be fully built in Phase 2
export default function Inbox() {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen bg-dark-900 flex items-center justify-center flex-col gap-4">
      <div className="text-center">
        <div className="text-5xl mb-4">🤖</div>
        <h1 className="text-2xl font-bold text-white">Hey, {user?.username}!</h1>
        <p className="text-gray-400 mt-2 text-sm">
          Auth is working. Inbox coming in Phase 2.
        </p>
      </div>
      <button
        onClick={logout}
        className="mt-4 px-6 py-2 bg-dark-700 hover:bg-dark-600 border border-dark-500
                   text-gray-300 rounded-xl text-sm transition-colors"
      >
        Sign out
      </button>
    </div>
  )
}
