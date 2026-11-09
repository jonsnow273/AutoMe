import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import api from '../utils/api'
import toast from 'react-hot-toast'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', password: '' })
  const [loading, setLoading] = useState(false)

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value })

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.username || !form.password) {
      toast.error('Please enter your username/email and password')
      return
    }
    setLoading(true)
    try {
      const { data: tokenData } = await api.post('/auth/login', form)
      const { data: userData } = await api.get('/auth/me', {
        headers: { Authorization: `Bearer ${tokenData.access_token}` }
      })
      login(tokenData.access_token, userData)
      toast.success(`Welcome back, ${userData.username}`)
      navigate('/inbox')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Invalid credentials')
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
          <h1 className="text-2xl font-bold text-white tracking-tight">Welcome back</h1>
          <p className="text-gray-400 mt-1 text-sm">Sign in to your AutoMe account</p>
        </div>

        {/* Card */}
        <div className="bg-dark-800 border border-dark-700 rounded-2xl p-8 shadow-xl">
          <form onSubmit={handleSubmit} className="space-y-5">

            {/* Username or Email */}
            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-2">
                Username or Email
              </label>
              <input
                type="text"
                name="username"
                value={form.username}
                onChange={handleChange}
                placeholder="your_username or you@email.com"
                className="w-full bg-dark-900 border border-dark-600 text-white rounded-xl px-4 py-2.5 text-sm
                           placeholder-gray-500 focus:outline-none focus:border-accent-500 focus:ring-1
                           focus:ring-accent-500 transition-colors"
              />
            </div>

            {/* Password */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-xs font-semibold text-gray-300">
                  Password
                </label>
                <Link
                  to="/forgot-password"
                  className="text-xs text-accent-400 hover:text-accent-300 font-medium transition-colors"
                >
                  Forgot password?
                </Link>
              </div>
              <input
                type="password"
                name="password"
                value={form.password}
                onChange={handleChange}
                placeholder="••••••••"
                className="w-full bg-dark-900 border border-dark-600 text-white rounded-xl px-4 py-2.5 text-sm
                           placeholder-gray-500 focus:outline-none focus:border-accent-500 focus:ring-1
                           focus:ring-accent-500 transition-colors"
              />
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-accent-600 hover:bg-accent-500 disabled:opacity-50 disabled:cursor-not-allowed
                         text-white font-semibold rounded-xl py-3 text-sm transition-colors flex items-center
                         justify-center gap-2 shadow-lg shadow-accent-600/20"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Signing in...
                </>
              ) : 'Sign In'}
            </button>
          </form>
        </div>

        {/* Footer link */}
        <p className="text-center text-gray-400 text-sm mt-6">
          Don't have an account?{' '}
          <Link to="/signup" className="text-accent-400 hover:text-accent-300 font-medium transition-colors">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  )
}
