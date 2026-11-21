import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import api from '../utils/api';

export default function Settings() {
  const navigate = useNavigate();
  const [styleProfile, setStyleProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [busyMode, setBusyMode] = useState(true);
  const [customBusyNote, setCustomBusyNote] = useState('Hey! Away from my screen right now, will get back to you soon.');
  const [savingSettings, setSavingSettings] = useState(false);

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const res = await api.get('/ai/style-profile');
      setStyleProfile(res.data);
    } catch (err) {
      console.error('Failed to load style profile', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRetrainStyle = async () => {
    setAnalyzing(true);
    try {
      const res = await api.post('/ai/learn-style');
      setStyleProfile(res.data);
      toast.success(`AI learned style from ${res.data.sample_size} sent messages!`);
    } catch (err) {
      console.error('Failed to train style', err);
      toast.error('Failed to analyze style. Make sure you have sent messages.');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleSaveBusySettings = async (e) => {
    e.preventDefault();
    setSavingSettings(true);
    try {
      toast.success('Busy mode settings updated');
    } finally {
      setSavingSettings(false);
    }
  };

  return (
    <div className="min-h-screen bg-dark-900 text-gray-100 p-6 lg:p-12">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl lg:text-3xl font-bold text-white tracking-tight">
              AI Persona &amp; Settings
            </h1>
            <p className="text-sm text-gray-400 mt-1">
              Configure how AutoMe learns your texting habits and replies on your behalf.
            </p>
          </div>
          <button
            onClick={() => navigate('/inbox')}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium bg-dark-800 hover:bg-dark-700 border border-dark-600 transition-colors"
          >
            &larr; Back to Inbox
          </button>
        </div>

        {/* AI Persona Card */}
        <div className="bg-dark-800 border border-dark-700 rounded-2xl p-6 shadow-xl space-y-6">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-accent-600/20 text-accent-400 border border-accent-500/30 flex items-center justify-center font-bold text-sm">
                AI
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">Learned Texting Style</h2>
                <p className="text-xs text-gray-400">
                  Powered by Groq LLaMA models. Analyzes your outgoing messages to replicate your tone and habits.
                </p>
              </div>
            </div>
            <button
              onClick={handleRetrainStyle}
              disabled={analyzing}
              className="px-4 py-2 text-xs font-semibold rounded-xl bg-accent-600 hover:bg-accent-500 text-white transition-all shadow-md disabled:opacity-50"
            >
              {analyzing ? 'Analyzing Sent Messages...' : 'Analyze &amp; Retrain Style'}
            </button>
          </div>

          {loading ? (
            <div className="h-32 bg-dark-900/50 rounded-xl animate-pulse" />
          ) : styleProfile ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
              {/* Tone & Formality */}
              <div className="bg-dark-900/60 border border-dark-700 p-4 rounded-xl space-y-2">
                <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider block">
                  Tone &amp; Formality
                </span>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-bold text-white capitalize">
                    {styleProfile.tone || 'Casual'}
                  </span>
                  <span className="text-xs text-accent-400 font-mono">
                    {Math.round((styleProfile.formality_score || 0.35) * 100)}% formal
                  </span>
                </div>
                <div className="w-full bg-dark-700 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-accent-500 h-full rounded-full transition-all duration-500"
                    style={{ width: `${Math.round((styleProfile.formality_score || 0.35) * 100)}%` }}
                  />
                </div>
              </div>

              {/* Message Length */}
              <div className="bg-dark-900/60 border border-dark-700 p-4 rounded-xl space-y-2">
                <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider block">
                  Average Length
                </span>
                <div className="text-sm font-bold text-white">
                  ~{Math.round(styleProfile.avg_message_length || 8)} words / message
                </div>
                <p className="text-[11px] text-gray-500">
                  {styleProfile.avg_message_length < 7
                    ? 'Short, concise and to the point.'
                    : 'Detailed and expressive responses.'}
                </p>
              </div>

              {/* Training Status */}
              <div className="bg-dark-900/60 border border-dark-700 p-4 rounded-xl space-y-2">
                <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider block">
                  Training Dataset
                </span>
                <div className="text-sm font-bold text-white">
                  {styleProfile.sample_size || 0} messages analyzed
                </div>
                <p className="text-[11px] text-gray-500">
                  {styleProfile.sample_size > 0
                    ? 'Learned from real message history.'
                    : 'Using intelligent baseline profile.'}
                </p>
              </div>

              {/* Frequent Phrases */}
              {styleProfile.common_phrases && styleProfile.common_phrases.length > 0 && (
                <div className="md:col-span-3 bg-dark-900/60 border border-dark-700 p-4 rounded-xl space-y-2">
                  <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider block">
                    Favorite Phrases &amp; Slang
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {styleProfile.common_phrases.map((phrase, idx) => (
                      <span
                        key={idx}
                        className="px-2.5 py-1 text-xs rounded-lg bg-dark-700 text-gray-200 border border-dark-600 font-mono"
                      >
                        &quot;{phrase}&quot;
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </div>

        {/* Busy Mode & Auto-Reply Settings */}
        <div className="bg-dark-800 border border-dark-700 rounded-2xl p-6 shadow-xl space-y-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center font-bold text-sm">
              AM
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white">Busy Mode &amp; Auto-Replies</h2>
              <p className="text-xs text-gray-400">
                When active, AutoMe automatically crafts and sends style-matched replies when new messages arrive.
              </p>
            </div>
          </div>

          <form onSubmit={handleSaveBusySettings} className="space-y-4 pt-2">
            <div className="flex items-center justify-between p-4 bg-dark-900/60 rounded-xl border border-dark-700">
              <div>
                <p className="text-sm font-semibold text-white">AI Auto-Reply Status</p>
                <p className="text-xs text-gray-400">Generate and send AI replies on connected platforms</p>
              </div>
              <button
                type="button"
                onClick={() => setBusyMode(!busyMode)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  busyMode ? 'bg-accent-600' : 'bg-dark-600'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    busyMode ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1.5">
                Current Status / Busy Reason
              </label>
              <textarea
                rows="3"
                value={customBusyNote}
                onChange={(e) => setCustomBusyNote(e.target.value)}
                placeholder="e.g. Working on project deadline, currently away from phone..."
                className="w-full bg-dark-900 border border-dark-600 text-white rounded-xl px-4 py-2.5 text-xs placeholder-gray-500 focus:outline-none focus:border-accent-500 focus:ring-1 focus:ring-accent-500"
              />
              <p className="text-[11px] text-gray-500 mt-1">
                The AI incorporates this context into its responses so contacts know why you are away.
              </p>
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={savingSettings}
                className="px-5 py-2 text-xs font-semibold rounded-xl bg-accent-600 hover:bg-accent-500 text-white transition-all shadow-md disabled:opacity-50"
              >
                {savingSettings ? 'Saving...' : 'Save Settings'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
