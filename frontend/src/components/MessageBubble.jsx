import { useMemo } from 'react';
import MoodBadge from './MoodBadge';
import PlatformBadge from './PlatformBadge';
import { formatTime } from '../utils/formatTime';

export default function MessageBubble({ message, contact, showContactInfo = false }) {
  const isOutgoing = message.direction === 'outgoing';

  const bubbleClass = useMemo(() =>
    `max-w-[70%] px-4 py-2 rounded-2xl ${isOutgoing
      ? 'bg-accent-500 text-white rounded-br-md ml-auto'
      : 'bg-dark-700 text-white rounded-bl-md mr-auto border border-dark-600'
    }`, [isOutgoing]);

  const time = useMemo(() => formatTime(message.timestamp), [message.timestamp]);

  return (
    <div className={`flex ${isOutgoing ? 'justify-end' : 'justify-start'} mb-3`}>
      {!isOutgoing && showContactInfo && contact && (
        <div className="w-8 h-8 flex-shrink-0 mr-2">
          {contact.avatar_url ? (
            <img src={contact.avatar_url} alt={contact.display_name || contact.username} className="w-8 h-8 rounded-full object-cover" />
          ) : (
            <div className="w-8 h-8 rounded-full bg-dark-600 flex items-center justify-center text-sm">
              {(contact.display_name || contact.username || '?')[0].toUpperCase()}
            </div>
          )}
        </div>
      )}

      <div className={isOutgoing ? 'flex flex-col items-end' : 'flex flex-col items-start'}>
        {!isOutgoing && showContactInfo && contact && (
          <div className="flex items-center gap-2 mb-1 ml-1">
            <span className="text-xs font-medium text-gray-300">{contact.display_name || contact.username}</span>
            <PlatformBadge platform={message.platform} />
            <MoodBadge mood={message.mood} />
          </div>
        )}

        <div className={bubbleClass}>
          <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
        </div>

        <div className={`flex items-center gap-1 text-xs text-gray-500 mt-1 ${isOutgoing ? 'mr-1' : 'ml-1'}`}>
          <span>{time}</span>
          {isOutgoing && message.is_read && <span className="text-accent-400">✓✓</span>}
          {isOutgoing && !message.is_read && <span className="text-gray-500">✓</span>}
        </div>

        {message.suggested_reply && !isOutgoing && (
          <div className="mt-2 p-2 bg-dark-800 border border-dark-600 rounded-xl text-xs text-gray-400 max-w-[70%]">
            <span className="font-medium text-accent-400">Suggested: </span>
            {message.suggested_reply}
          </div>
        )}
      </div>

      {isOutgoing && showContactInfo && (
        <div className="w-8 h-8 flex-shrink-0 ml-2" />
      )}
    </div>
  );
}