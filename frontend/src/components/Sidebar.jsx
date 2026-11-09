import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useContacts } from '../hooks/useMessages';
import { useMessageSocket } from '../hooks/useSocket';
import { useAuth } from '../hooks/useAuth';
import PlatformBadge from './PlatformBadge';
import { formatTime } from '../utils/formatTime';
import api from '../utils/api';

export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const { newMessage } = useMessageSocket();
  const [search, setSearch] = useState('');
  const [selectedPlatform, setSelectedPlatform] = useState(null);
  const [hasConnectedPlatform, setHasConnectedPlatform] = useState(false);

  useEffect(() => {
    api.get('/platforms').then((res) => {
      const anyConnected = (res.data || []).some((p) => p.is_connected);
      setHasConnectedPlatform(anyConnected);
    }).catch(() => {});
  }, []);

  // Extract contactId from pathname
  const match = location.pathname.match(/\/inbox\/(\d+)/);
  const currentContactId = match ? parseInt(match[1]) : null;

  // Fetch contacts
  const { data: contactsData, isLoading, refetch } = useContacts({
    search: search || undefined,
    platform: selectedPlatform || undefined,
  });

  useEffect(() => {
    if (newMessage) {
      refetch();
    }
  }, [newMessage, refetch]);

  useEffect(() => {
    refetch();
  }, [search, selectedPlatform, refetch]);

  const contacts = contactsData?.contacts || [];

  const getDisplayName = (contact) => {
    return contact.display_name || contact.username || `User ${contact.platform_user_id}`;
  };

  const getLastMessagePreview = (contact) => {
    if (!contact.last_message_preview) return 'No messages yet';
    return contact.last_message_preview.length > 45
      ? contact.last_message_preview.substring(0, 45) + '...'
      : contact.last_message_preview;
  };

  return (
    <div className="flex-1 flex flex-col h-full min-w-0 bg-dark-800 text-gray-200">
      {/* Top Header */}
      <div className="p-4 border-b border-dark-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-accent-600 font-bold text-white text-xs flex items-center justify-center">
            AM
          </div>
          <span className="font-bold text-white tracking-wide">AutoMe</span>
        </div>
        <button
          onClick={() => navigate('/platforms')}
          className="px-3 py-1.5 text-xs font-semibold rounded-xl bg-accent-600/20 text-accent-400 hover:bg-accent-600/30 border border-accent-500/30 transition-all flex items-center gap-1.5"
          title="Connect Platforms"
        >
          <span>Platforms</span>
        </button>
      </div>

      {/* Search & Filter */}
      <div className="p-3 space-y-2 border-b border-dark-700">
        <div className="relative">
          <input
            type="text"
            placeholder="Search conversations..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-dark-900 border border-dark-700 text-white rounded-xl px-3.5 py-2 text-xs placeholder-gray-500 focus:outline-none focus:border-accent-500 transition-colors pl-8"
          />
          <svg
            className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>

        <div className="flex gap-1.5 overflow-x-auto pb-1">
          {['All', 'discord', 'whatsapp', 'instagram'].map((p) => (
            <button
              key={p}
              onClick={() => setSelectedPlatform(p === 'All' ? null : p)}
              className={`whitespace-nowrap px-2.5 py-1 rounded-lg text-[11px] font-medium transition-colors ${
                (p === 'All' && !selectedPlatform) || selectedPlatform === p
                  ? 'bg-accent-600 text-white shadow-sm'
                  : 'bg-dark-700/60 text-gray-400 hover:bg-dark-700 hover:text-gray-200'
              }`}
            >
              {p.charAt(0).toUpperCase() + p.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Contact List */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="p-3 space-y-2">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-16 bg-dark-700/50 rounded-xl animate-pulse" />
            ))}
          </div>
        ) : contacts.length === 0 ? (
          <div className="h-full flex items-center justify-center p-6 text-center">
            <div className="space-y-2">
              <p className="text-xs text-gray-300 font-medium">No conversations yet</p>
              {hasConnectedPlatform ? (
                <p className="text-[11px] text-gray-500 max-w-[200px] leading-relaxed">
                  Discord is connected. Send a direct message to your bot on Discord to see it appear here.
                </p>
              ) : (
                <button
                  onClick={() => navigate('/platforms')}
                  className="text-xs text-accent-400 hover:underline inline-block mt-1"
                >
                  Connect Discord to start →
                </button>
              )}
            </div>
          </div>
        ) : (
          <ul className="divide-y divide-dark-700/50">
            {contacts.map((contact) => {
              const isActive = currentContactId === contact.id;
              return (
                <li key={contact.id}>
                  <button
                    onClick={() => navigate(`/inbox/${contact.id}`)}
                    className={`w-full px-3.5 py-3 text-left transition-all flex items-center gap-3 ${
                      isActive
                        ? 'bg-accent-600/10 border-l-4 border-accent-500'
                        : 'hover:bg-dark-700/40'
                    }`}
                  >
                    {/* Avatar */}
                    <div className="relative flex-shrink-0">
                      {contact.avatar_url ? (
                        <img
                          src={contact.avatar_url}
                          alt={getDisplayName(contact)}
                          className="w-10 h-10 rounded-full object-cover border border-dark-600"
                        />
                      ) : (
                        <div className="w-10 h-10 rounded-full bg-dark-700 border border-dark-600 flex items-center justify-center text-xs font-bold text-gray-300">
                          {getDisplayName(contact)[0].toUpperCase()}
                        </div>
                      )}
                      {contact.unread_count > 0 && (
                        <span className="absolute -top-1 -right-1 w-4 h-4 bg-accent-500 text-white text-[10px] rounded-full flex items-center justify-center font-bold">
                          {contact.unread_count}
                        </span>
                      )}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1">
                        <span className={`text-xs font-semibold truncate ${isActive ? 'text-white' : 'text-gray-200'}`}>
                          {getDisplayName(contact)}
                        </span>
                        <span className="text-[10px] text-gray-500 whitespace-nowrap">
                          {contact.last_message_time ? formatTime(contact.last_message_time) : ''}
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5 mt-1">
                        <PlatformBadge platform={contact.platform} />
                        <span className="text-[11px] text-gray-400 truncate">
                          {getLastMessagePreview(contact)}
                        </span>
                      </div>
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-dark-700 flex items-center justify-between bg-dark-850">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-full bg-accent-600/30 text-accent-300 flex items-center justify-center text-xs font-bold border border-accent-500/20">
            {user?.username?.[0]?.toUpperCase() || 'U'}
          </div>
          <div className="truncate">
            <p className="text-xs font-semibold text-white truncate">{user?.username}</p>
            <span className="text-[10px] text-emerald-400 font-medium">Online</span>
          </div>
        </div>

        <button
          onClick={logout}
          className="text-xs text-gray-400 hover:text-rose-400 transition-colors px-2 py-1"
          title="Sign Out"
        >
          Sign out
        </button>
      </div>
    </div>
  );
}
