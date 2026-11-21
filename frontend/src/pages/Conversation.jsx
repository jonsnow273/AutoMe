import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useConversation, useMarkMessagesRead } from '../hooks/useMessages';
import { useContact } from '../hooks/useMessages';
import { useMessageSocket } from '../hooks/useSocket';
import { useAuth } from '../hooks/useAuth';
import MessageBubble from '../components/MessageBubble';
import { formatTime, formatFullTime } from '../utils/formatTime';
import api from '../utils/api';

export default function Conversation() {
  const { contactId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { newMessage } = useMessageSocket();
  const [replyText, setReplyText] = useState('');
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef(null);
  const [showContactInfo, setShowContactInfo] = useState(true);

  const [generatingAi, setGeneratingAi] = useState(false);
  const [currentSuggestion, setCurrentSuggestion] = useState(null);

  const contactIdNum = parseInt(contactId);
  const { data: conversationData, isLoading, refetch } = useConversation(contactIdNum);
  const { data: contact } = useContact(contactIdNum);
  const { mutate: markRead } = useMarkMessagesRead();

  const messages = conversationData?.messages || [];
  const latestIncoming = [...messages].reverse().find(m => m.direction === 'incoming');

  useEffect(() => {
    if (latestIncoming?.suggested_reply) {
      setCurrentSuggestion({
        reply: latestIncoming.suggested_reply,
        confidence: latestIncoming.reply_confidence || 85,
        mood: latestIncoming.mood,
      });
    } else {
      setCurrentSuggestion(null);
    }
  }, [latestIncoming?.id, latestIncoming?.suggested_reply]);

  const handleGenerateAiReply = async () => {
    if (!latestIncoming) return;
    setGeneratingAi(true);
    try {
      const res = await api.post('/ai/suggest-reply', {
        message_id: latestIncoming.id,
      });
      setCurrentSuggestion({
        reply: res.data.reply,
        confidence: res.data.confidence,
        mood: res.data.mood,
      });
      toast.success('AI reply suggestion ready');
      refetch();
    } catch (err) {
      console.error('Failed to generate AI suggestion', err);
      toast.error('Failed to generate AI reply');
    } finally {
      setGeneratingAi(false);
    }
  };

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversationData]);

  // Refetch when new message arrives
  useEffect(() => {
    if (newMessage && newMessage.message?.contact_id === contactIdNum) {
      refetch();
    }
  }, [newMessage, contactIdNum, refetch]);

  // Mark as read when conversation loads
  useEffect(() => {
    if (conversationData?.messages?.length) {
      const unreadIds = conversationData.messages
        .filter(m => m.direction === 'incoming' && !m.is_read)
        .map(m => m.id);
      if (unreadIds.length > 0) {
        markRead(unreadIds);
      }
    }
  }, [conversationData, markRead]);

  const handleSendReply = async (e) => {
    e.preventDefault();
    if (!replyText.trim() || sending) return;

    setSending(true);
    try {
      // Send via backend (which forwards to platform)
      await api.post('/messages/send', {
        contact_id: contactIdNum,
        content: replyText.trim(),
      });
      setReplyText('');
      refetch();
    } catch (err) {
      console.error('Failed to send reply:', err);
      alert('Failed to send message');
    } finally {
      setSending(false);
    }
  };

  const getDisplayName = () => {
    if (!contact) return 'Unknown';
    return contact.display_name || contact.username || `User ${contact.platform_user_id}`;
  };

  if (isLoading && !conversationData) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-accent-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!contact) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-500">
        Contact not found
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-w-0 bg-dark-900">
      {/* Contact Header */}
      <div className="px-4 py-3 border-b border-dark-700 flex items-center gap-3 bg-dark-800/50 backdrop-blur sticky top-0 z-10">
        <button
          onClick={() => navigate('/inbox')}
          className="p-1 hover:bg-dark-700 rounded-lg transition-colors lg:hidden"
        >
          ←
        </button>

        <div className="relative flex-shrink-0">
          {contact.avatar_url ? (
            <img src={contact.avatar_url} alt={getDisplayName()} className="w-10 h-10 rounded-full object-cover" />
          ) : (
            <div className="w-10 h-10 rounded-full bg-dark-600 flex items-center justify-center text-lg font-medium">
              {getDisplayName()[0].toUpperCase()}
            </div>
          )}
        </div>

        <div className="flex-1 min-w-0">
          <p className="font-medium text-white truncate">{getDisplayName()}</p>
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <span>•</span>
            <span>{contact.platform}</span>
            <span>•</span>
            <span>{contact.relationship_type || 'Unknown'}</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowContactInfo(!showContactInfo)}
            className="px-2.5 py-1 text-xs bg-dark-700 hover:bg-dark-600 rounded-lg transition-colors text-gray-300"
            title="Toggle contact info in messages"
          >
            {showContactInfo ? 'Hide Details' : 'Show Details'}
          </button>
        </div>
      </div>

      {/* Messages List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-1" ref={messagesEndRef}>
        {messages.length === 0 ? (
          <div className="flex-1 flex items-center justify-center text-gray-500 py-12">
            <div className="text-center">
              <p className="text-sm text-gray-300 font-medium">No messages yet</p>
              <p className="text-xs text-gray-500 mt-1">Start the conversation below</p>
            </div>
          </div>
        ) : (
          messages.map((message, index) => {
            const prevMessage = messages[index - 1];
            const showContactInfoForThis = showContactInfo &&
              message.direction === 'incoming' &&
              (!prevMessage || prevMessage.direction !== 'incoming');

            return (
              <MessageBubble
                key={message.id}
                message={message}
                contact={contact}
                showContactInfo={showContactInfoForThis}
              />
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Reply Input & AI Suggestion */}
      <div className="p-4 border-t border-dark-700 bg-dark-800/50 backdrop-blur sticky bottom-0 z-10 space-y-3">
        {/* AI Suggestion Bar */}
        {latestIncoming && (
          <div className="p-3 bg-dark-800 border border-dark-600 rounded-xl flex items-center justify-between gap-3 text-xs shadow-md">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-semibold text-accent-400">AI Suggestion</span>
                {currentSuggestion?.confidence ? (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-accent-600/20 text-accent-300 font-mono">
                    {currentSuggestion.confidence}% match
                  </span>
                ) : null}
                {currentSuggestion?.mood ? (
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-dark-700 text-gray-300 capitalize">
                    {currentSuggestion.mood}
                  </span>
                ) : null}
              </div>
              <p className="text-gray-300 truncate font-mono text-[11px]">
                {currentSuggestion?.reply || 'Click generate to create an intelligent style-matched response.'}
              </p>
            </div>

            <div className="flex items-center gap-2 flex-shrink-0">
              {currentSuggestion?.reply && (
                <button
                  type="button"
                  onClick={() => setReplyText(currentSuggestion.reply)}
                  className="px-3 py-1.5 bg-accent-600 hover:bg-accent-500 text-white rounded-lg font-semibold transition-all shadow-sm"
                >
                  Use Suggestion
                </button>
              )}
              <button
                type="button"
                onClick={handleGenerateAiReply}
                disabled={generatingAi}
                className="px-2.5 py-1.5 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-lg transition-colors disabled:opacity-50"
              >
                {generatingAi ? 'Generating...' : currentSuggestion?.reply ? 'Regenerate' : 'Generate with AI'}
              </button>
            </div>
          </div>
        )}

        <form onSubmit={handleSendReply} className="flex items-center gap-2">
          <input
            type="text"
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            placeholder="Type a reply..."
            disabled={sending}
            className="flex-1 bg-dark-700 border border-dark-500 text-white rounded-xl px-4 py-3 text-sm
                       placeholder-gray-500 focus:outline-none focus:border-accent-500 focus:ring-1
                       focus:ring-accent-500 transition-colors disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={sending || !replyText.trim()}
            className="bg-accent-500 hover:bg-accent-600 disabled:opacity-50 disabled:cursor-not-allowed
                       text-white font-semibold rounded-xl px-6 py-3 text-sm transition-colors flex items-center justify-center"
          >
            {sending ? 'Sending...' : 'Send'}
          </button>
        </form>
      </div>
    </div>
  );
}