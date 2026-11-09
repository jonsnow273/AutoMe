import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../utils/api'
import toast from 'react-hot-toast'

export default function ForgotPassword() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    identifier: '',
    new_password: '',
    confirm_password: '',
  })
  const [loading, setLoading] = useState(false)
  const [recoveredUsername, setRecoveredUsername] = useState(null)

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value })

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.identifier || !form.new_password || !form.confirm_password) {
      toast.error('Please fill in all fields')
      return
    }

    if (form.new_password.length < 6) {
      toast.error('Password must be at least 6 characters')
      return
    }

    if (form.new_password !== form.confirm_password) {
      toast.error('Passwords do not match')
      return
    }

    setLoading(true)
    try {
      const res = await api.post('/auth/reset-password', {
        identifier: form.identifier.trim(),
        new_password: form.new_password,
      })
      setRecoveredUsername(res.data.username)
      toast.success(res.data.message || 'Password reset successfully')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reset password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-dark-900 flex items-center justify-center px-4">
      <div className="w-full max-w-md">

        {/* Brand */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-accent-600 font-bold text-white text-lg mb-4 shadow-lg shadow-accent-600/30">
            AM
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Reset Password</h1>
          <p className="text-gray-400 mt-1 text-sm">
            Enter your username or email to set a new password
          </p>
        </div>

        {/* Card */}
        <div className="bg-dark-800 border border-dark-700 rounded-2xl p-8 shadow-xl">
          {recoveredUsername ? (
            <div className="space-y-5 text-center">
              <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm">
                Password updated successfully.
              </div>
              <p className="text-xs text-gray-300">
                Your registered username is:{' '}
                <strong className="text-white font-mono bg-dark-900 px-2 py-1 rounded">
                  {recoveredUsername}
                </strong>
              </p>
              <button
                onClick={() => navigate('/login')}
                className="w-full bg-accent-600 hover:bg-accent-500 text-white font-semibold rounded-xl py-3 text-sm transition-colors shadow-lg shadow-accent-600/20"
              >
                Sign In Now
              </button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1.5">
                  Username or Email
                </label>
                <input
                  type="text"
                  name="identifier"
                  value={form.identifier}
                  onChange={handleChange}
                  placeholder="your_username or you@email.com"
                  required
                  className="w-full bg-dark-900 border border-dark-600 text-white rounded-xl px-4 py-2.5 text-sm placeholder-gray-500 focus:outline-none focus:border-accent-500 focus:ring-1 focus:ring-accent-500 transition-colors"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1.5">
                  New Password
                </label>
                <input
                  type="password"
                  name="new_password"
                  value={form.new_password}
                  onChange={handleChange}
                  placeholder="At least 6 characters"
                  required
                  className="w-full bg-dark-900 border border-dark-600 text-white rounded-xl px-4 py-2.5 text-sm placeholder-gray-500 focus:outline-none focus:border-accent-500 focus:ring-1 focus:ring-accent-500 transition-colors"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1.5">
                  Confirm New Password
                </label>
                <input
                  type="password"
                  name="confirm_password"
                  value={form.confirm_password}
                  onChange={handleChange}
                  placeholder="Re-enter new password"
                  required
                  className="w-full bg-dark-900 border border-dark-600 text-white rounded-xl px-4 py-2.5 text-sm placeholder-gray-500 focus:outline-none focus:border-accent-500 focus:ring-1 focus:ring-accent-500 transition-colors"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-accent-600 hover:bg-accent-500 disabled:opacity-50 text-white font-semibold rounded-xl py-3 text-sm transition-colors shadow-lg shadow-accent-600/20 mt-2"
              >
                {loading ? 'Updating Password...' : 'Reset Password'}
              </button>
            </form>
          )}
        </div>

        {/* Footer */}
        <p className="text-center text-gray-400 text-sm mt-6">
          Remember your password?{' '}
          <Link to="/login" className="text-accent-400 hover:text-accent-300 font-medium transition-colors">
            Back to Sign In
          </Link>
        </p>
      </div>
    </div>
  )
}
