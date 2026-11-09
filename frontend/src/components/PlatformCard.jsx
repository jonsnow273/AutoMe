import { useState } from 'react';
import toast from 'react-hot-toast';

export default function PlatformCard({
  platform,
  platformRecord,
  onConnect,
  onDisconnect,
  onReconnect,
  loading,
}) {
  const [token, setToken] = useState('');
  const [showToken, setShowToken] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);

  const isConnected = !!platformRecord?.is_connected;
  const hasError = !!platformRecord?.error_message && !isConnected;

  const handleConnect = async (e) => {
    e.preventDefault();
    if (!token.trim()) {
      toast.error('Please enter a valid bot token');
      return;
    }
    await onConnect(platform.id, { bot_token: token.trim() });
    setToken('');
    setIsExpanded(false);
  };

  return (
    <div className="bg-dark-800 border border-dark-700 rounded-2xl p-6 transition-all hover:border-dark-600 shadow-xl">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className={`w-12 h-12 rounded-xl flex items-center justify-center font-bold text-sm tracking-wider ${platform.bgColor} ${platform.textColor}`}>
            {platform.tag}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-semibold text-white">{platform.name}</h3>
              <span
                className={`text-xs px-2.5 py-0.5 rounded-full font-medium ${
                  isConnected
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                    : hasError
                    ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                    : 'bg-dark-700 text-gray-400 border border-dark-600'
                }`}
              >
                {isConnected ? 'Connected' : hasError ? 'Connection Error' : 'Disconnected'}
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-1">{platform.description}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* If record exists and not connected, offer 1-click Reconnect */}
          {platformRecord && !isConnected && onReconnect && (
            <button
              onClick={() => onReconnect(platform.id)}
              disabled={loading}
              className="px-3 py-1.5 rounded-xl text-xs font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 hover:bg-emerald-500/20 transition-all disabled:opacity-50"
            >
              {loading ? 'Reconnecting...' : 'Reconnect'}
            </button>
          )}

          {/* If record exists in DB, always give Disconnect/Reset option */}
          {platformRecord && (
            <button
              onClick={() => onDisconnect(platform.id)}
              disabled={loading}
              className="px-3 py-1.5 rounded-xl text-xs font-semibold text-rose-400 bg-rose-500/10 border border-rose-500/20 hover:bg-rose-500/20 transition-all disabled:opacity-50"
              title="Remove and disconnect"
            >
              {loading ? 'Disconnecting...' : 'Disconnect'}
            </button>
          )}

          {/* Connect or Change Token button */}
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="px-4 py-1.5 rounded-xl text-xs font-semibold text-white bg-accent-600 hover:bg-accent-500 transition-all shadow-md hover:shadow-accent-500/25"
          >
            {isExpanded ? 'Cancel' : isConnected ? 'Change Token' : 'Connect'}
          </button>
        </div>
      </div>

      {/* Error alert if any */}
      {hasError && (
        <div className="mt-4 p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-xs text-rose-400 flex items-start justify-between gap-3">
          <div>
            <span className="font-semibold block mb-0.5">Connection Failed:</span>
            <span>{platformRecord.error_message}</span>
          </div>
          <div className="flex items-center gap-2">
            {onReconnect && (
              <button
                onClick={() => onReconnect(platform.id)}
                disabled={loading}
                className="text-xs font-semibold px-2 py-0.5 bg-rose-500/20 rounded-md hover:bg-rose-500/30 text-rose-200"
              >
                Reconnect
              </button>
            )}
            <button
              onClick={() => onDisconnect(platform.id)}
              className="text-xs underline hover:text-rose-300 font-medium whitespace-nowrap"
            >
              Reset
            </button>
          </div>
        </div>
      )}

      {/* Expanded connect/reconnect form */}
      {isExpanded && (
        <form onSubmit={handleConnect} className="mt-5 pt-5 border-t border-dark-700 space-y-4 animate-in fade-in duration-200">
          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1.5">
              Discord Account Token (Alt Account)
            </label>
            <div className="relative">
              <input
                type={showToken ? 'text' : 'password'}
                placeholder="Paste your Discord Account Token here..."
                value={token}
                onChange={(e) => setToken(e.target.value)}
                required
                className="w-full bg-dark-900 border border-dark-600 text-white rounded-xl px-4 py-2.5 text-xs font-mono placeholder-gray-500 focus:outline-none focus:border-accent-500 focus:ring-1 focus:ring-accent-500 pr-16"
              />
              <button
                type="button"
                onClick={() => setShowToken(!showToken)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400 hover:text-gray-200"
              >
                {showToken ? 'Hide' : 'Show'}
              </button>
            </div>
            <div className="text-[11px] text-gray-400 mt-2 space-y-1 bg-dark-900/60 p-3 rounded-xl border border-dark-700">
              <p className="font-semibold text-gray-300">Important Checklist for Discord Bot:</p>
              <p>1. Copy the <strong>Token</strong> from Discord Developer Portal → Your App → <strong>Bot</strong> tab → <strong>Reset Token</strong>.</p>
              <p>2. Scroll down on the <strong>Bot</strong> tab to <strong>Privileged Gateway Intents</strong> and enable <strong>Message Content Intent</strong>.</p>
              <p>3. Do NOT copy the Client Secret or Application ID from General Information.</p>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={() => setIsExpanded(false)}
              className="px-3 py-1.5 text-xs text-gray-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-1.5 text-xs font-semibold text-white bg-accent-600 hover:bg-accent-500 rounded-xl transition-all shadow-md disabled:opacity-50"
            >
              {loading ? 'Verifying & Starting...' : 'Save & Connect'}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
