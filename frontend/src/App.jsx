import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { useAuth } from './hooks/useAuth'
import Login from './pages/Login'
import Signup from './pages/Signup'
import ForgotPassword from './pages/ForgotPassword'
import Inbox from './pages/Inbox'
import Conversation from './pages/Conversation'
import EmptyConversation from './components/EmptyConversation'
import ConnectPlatforms from './pages/ConnectPlatforms'

// Spinner shown while auth state loads
function Spinner() {
  return (
    <div className="flex items-center justify-center h-screen bg-dark-900">
      <div className="w-8 h-8 border-2 border-accent-500 border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

// Only accessible when logged in
function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <Spinner />
  return user ? children : <Navigate to="/login" replace />
}

// Only accessible when NOT logged in
function PublicRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <Spinner />
  return user ? <Navigate to="/inbox" replace /> : children
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/inbox" replace />} />
      <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
      <Route path="/signup" element={<PublicRoute><Signup /></PublicRoute>} />
      <Route path="/forgot-password" element={<PublicRoute><ForgotPassword /></PublicRoute>} />
      <Route element={<ProtectedRoute><Inbox /></ProtectedRoute>}>
        <Route path="/inbox" element={<EmptyConversation />} />
        <Route path="/inbox/:contactId" element={<Conversation />} />
      </Route>
      <Route path="/platforms" element={<ProtectedRoute><ConnectPlatforms /></ProtectedRoute>} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}
