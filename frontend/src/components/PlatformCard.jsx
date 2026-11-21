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
  // Discord state
  const [discordToken, setDiscordToken] = useState('');
  const [showDiscordToken, setShowDiscordToken] = useState(false);

  // Instagram state
  const [igMode, setIgMode] = useState('cookie'); // 'cookie' or 'credentials'
  const [igSessionId, setIgSessionId] = useState('');
  const [showIgSessionId, setShowIgSessionId] = useState(false);
  const [igUsername, setIgUsername] = useState('');
  const [igPassword, setIgPassword] = useState('');
  const [showIgPassword, setShowIgPassword] = useState(false);
  const [ig2faCode, setIg2faCode] = useState('');

  const [isExpanded, setIsExpanded] = useState(false);

  const isConnected = !!platformRecord?.is_connected;
  const hasError = !!platformRecord?.error_message && !isConnected;

  const handleConnect = async (e) => {
    e.preventDefault();

    if (platform.id === 'discord') {
      if (!discordToken.trim()) {
        toast.error('Please enter a valid Discord token');
        return;
      }
      await onConnect('discord', { bot_token: discordToken.trim() });
      setDiscordToken('');
      setIsExpanded(false);
    } else if (platform.id === 'instagram') {
      if (igMode === 'cookie') {
        if (!igSessionId.trim()) {
          toast.error('Please paste your Instagram sessionid cookie');
          return;
        }
        await onConnect('instagram', { sessionid: igSessionId.trim() });
      } else {
        if (!igUsername.trim() || !igPassword.trim()) {
          toast.error('Please enter your Instagram username and password');
          return;
        }
        await onConnect('instagram', {
          username: igUsername.trim(),
          password: igPassword.trim(),
          verification_code: ig2faCode.trim() || undefined,
        });
      }
      setIgSessionId('');
      setIgPassword('');
      setIg2faCode('');
      setIsExpanded(false);
    }
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
          {/* Reconnect button */}
          {platformRecord && !isConnected && onReconnect && (
            <button
              onClick={() => onReconnect(platform.id)}
              disabled={loading}
              className="px-3 py-1.5 rounded-xl text-xs font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 hover:bg-emerald-500/20 transition-all disabled:opacity-50"
            >
              {loading ? 'Reconnecting...' : 'Reconnect'}
            </button>
          )}

          {/* Disconnect button */}
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

          {/* Connect button */}
          {!isConnected && (
            <button
              onClick={() => {
                if (platform.id === 'whatsapp') {
                  onConnect(platform.id);
                } else {
                  setIsExpanded(!isExpanded);
                }
              }}
              className="px-4 py-1.5 rounded-xl text-xs font-semibold text-white bg-accent-600 hover:bg-accent-500 transition-all shadow-md hover:shadow-accent-500/25"
            >
              {isExpanded ? 'Cancel' : 'Connect'}
            </button>
          )}
        </div>
      </div>

      {/* Error alert */}
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

      {/* Expanded connect forms */}
      {isExpanded && platform.id === 'discord' && (
        <form onSubmit={handleConnect} className="mt-5 pt-5 border-t border-dark-700 space-y-4 animate-in fade-in duration-200">
          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1.5">
              Discord User Account Token (Alt Account)
            </label>
            <div className="relative">
              <input
                type={showDiscordToken ? 'text' : 'password'}
                placeholder="Paste your Discord User Account Token..."
                value={discordToken}
                onChange={(e) => setDiscordToken(e.target.value)}
                required
                className="w-full bg-dark-900 border border-dark-600 text-white rounded-xl px-4 py-2.5 text-xs font-mono placeholder-gray-500 focus:outline-none focus:border-accent-500 focus:ring-1 focus:ring-accent-500 pr-16"
              />
              <button
                type="button"
                onClick={() => setShowDiscordToken(!showDiscordToken)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400 hover:text-gray-200"
              >
                {showDiscordToken ? 'Hide' : 'Show'}
              </button>
            </div>
            <div className="text-[11px] text-gray-400 mt-2 space-y-1 bg-dark-900/60 p-3 rounded-xl border border-dark-700">
              <p className="font-semibold text-gray-300">How to get your Discord Token:</p>
              <p>1. Open Discord in your browser (e.g. Chrome) and log into your account.</p>
              <p>2. Press F12 &rarr; Network tab &rarr; click any request &rarr; find the &quot;Authorization&quot; header in Request Headers.</p>
              <p>3. Paste the authorization token here.</p>
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

      {/* Instagram Connect Form */}
      {isExpanded && platform.id === 'instagram' && (
        <form onSubmit={handleConnect} className="mt-5 pt-5 border-t border-dark-700 space-y-4 animate-in fade-in duration-200">
          {/* Method Selector Tabs */}
          <div className="flex gap-2 p-1 bg-dark-900 rounded-xl border border-dark-700">
            <button
              type="button"
              onClick={() => setIgMode('cookie')}
              className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                igMode === 'cookie'
                  ? 'bg-accent-600 text-white shadow-sm'
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              Session Cookie (Recommended)
            </button>
            <button
              type="button"
              onClick={() => setIgMode('credentials')}
              className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                igMode === 'credentials'
                  ? 'bg-accent-600 text-white shadow-sm'
                  : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              Username & Password
            </button>
          </div>

          {igMode === 'cookie' ? (
            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1.5">
                Instagram sessionid Cookie
              </label>
              <div className="relative">
                <input
                  type={showIgSessionId ? 'text' : 'password'}
                  placeholder="Paste your sessionid cookie..."
                  value={igSessionId}
                  onChange={(e) => setIgSessionId(e.target.value)}
                  required
                  className="w-full bg-dark-900 border border-dark-600 text-white rounded-xl px-4 py-2.5 text-xs font-mono placeholder-gray-500 focus:outline-none focus:border-accent-500 focus:ring-1 focus:ring-accent-500 pr-16"
                />
                <button
                  type="button"
                  onClick={() => setShowIgSessionId(!showIgSessionId)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400 hover:text-gray-200"
                >
                  {showIgSessionId ? 'Hide' : 'Show'}
                </button>
              </div>

              <div className="text-[11px] text-gray-400 mt-2 space-y-1 bg-dark-900/60 p-3 rounded-xl border border-dark-700">
                <p className="font-semibold text-gray-300">How to get your sessionid cookie (15 seconds):</p>
                <p>1. Open <strong>instagram.com</strong> in your browser and log in.</p>
                <p>2. Press <strong>F12</strong> to open Developer Tools, then go to the <strong>Application</strong> (or Storage) tab.</p>
                <p>3. In the left sidebar, click <strong>Cookies</strong> → <strong>https://www.instagram.com</strong>.</p>
                <p>4. Find <strong>sessionid</strong>, double-click its value, copy and paste it above.</p>
                <p className="text-accent-400 pt-0.5">Tip: Cookie login completely bypasses 2FA/SMS challenge checkpoints!</p>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1.5">
                  Instagram Username
                </label>
                <input
                  type="text"
                  placeholder="username (without @)"
                  value={igUsername}
                  onChange={(e) => setIgUsername(e.target.value)}
                  required
                  className="w-full bg-dark-900 border border-dark-600 text-white rounded-xl px-4 py-2 text-xs placeholder-gray-500 focus:outline-none focus:border-accent-500 focus:ring-1 focus:ring-accent-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1.5">
                  Instagram Password
                </label>
                <div className="relative">
                  <input
                    type={showIgPassword ? 'text' : 'password'}
                    placeholder="Enter your Instagram password..."
                    value={igPassword}
                    onChange={(e) => setIgPassword(e.target.value)}
                    required
                    className="w-full bg-dark-900 border border-dark-600 text-white rounded-xl px-4 py-2 text-xs placeholder-gray-500 focus:outline-none focus:border-accent-500 focus:ring-1 focus:ring-accent-500 pr-16"
                  />
                  <button
                    type="button"
                    onClick={() => setShowIgPassword(!showIgPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400 hover:text-gray-200"
                  >
                    {showIgPassword ? 'Hide' : 'Show'}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1.5">
                  2FA / Security Code (Optional)
                </label>
                <input
                  type="text"
                  placeholder="6-digit authentication code if 2FA is active"
                  value={ig2faCode}
                  onChange={(e) => setIg2faCode(e.target.value)}
                  className="w-full bg-dark-900 border border-dark-600 text-white rounded-xl px-4 py-2 text-xs placeholder-gray-500 focus:outline-none focus:border-accent-500 focus:ring-1 focus:ring-accent-500"
                />
              </div>
            </div>
          )}

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
              {loading ? 'Authenticating...' : 'Connect Instagram'}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
