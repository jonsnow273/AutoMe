import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../utils/api';

// Query keys
export const messageKeys = {
  all: ['messages'],
  lists: () => [...messageKeys.all, 'list'],
  list: (filters) => [...messageKeys.lists(), filters],
  conversation: (contactId) => [...messageKeys.all, 'conversation', contactId],
  unreadCount: () => [...messageKeys.all, 'unreadCount'],
};

export const contactKeys = {
  all: ['contacts'],
  lists: () => [...contactKeys.all, 'list'],
  list: (filters) => [...contactKeys.lists(), filters],
  detail: (contactId) => [...contactKeys.all, 'detail', contactId],
};

// ─── Messages ────────────────────────────────────────────────────────────────

export function useMessages(filters = {}) {
  return useQuery({
    queryKey: messageKeys.list(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.platform) params.append('platform', filters.platform);
      if (filters.contactId) params.append('contact_id', filters.contactId);
      if (filters.unreadOnly) params.append('unread_only', 'true');
      if (filters.page) params.append('page', filters.page);
      if (filters.pageSize) params.append('page_size', filters.pageSize);

      const { data } = await api.get(`/messages?${params.toString()}`);
      return data;
    },
    placeholderData: (previousData) => previousData,
  });
}

export function useConversation(contactId, enabled = true) {
  return useQuery({
    queryKey: messageKeys.conversation(contactId),
    queryFn: async () => {
      const { data } = await api.get(`/messages/conversation/${contactId}`);
      return data;
    },
    enabled: enabled && !!contactId,
    placeholderData: (previousData) => previousData,
  });
}

export function useUnreadCount() {
  return useQuery({
    queryKey: messageKeys.unreadCount(),
    queryFn: async () => {
      const { data } = await api.get('/messages/unread/count');
      return data.unread_count;
    },
    refetchInterval: 30000, // Poll every 30s as fallback
  });
}

export function useMarkMessageRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (messageId) => {
      await api.post(`/messages/${messageId}/read`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: messageKeys.unreadCount() });
      queryClient.invalidateQueries({ queryKey: messageKeys.lists() });
    },
  });
}

export function useMarkMessagesRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (messageIds) => {
      await api.post('/messages/read/batch', { message_ids: messageIds });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: messageKeys.unreadCount() });
      queryClient.invalidateQueries({ queryKey: messageKeys.lists() });
    },
  });
}

// ─── Contacts ────────────────────────────────────────────────────────────────

export function useContacts(filters = {}) {
  return useQuery({
    queryKey: contactKeys.list(filters),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.platform) params.append('platform', filters.platform);
      if (filters.search) params.append('search', filters.search);

      const { data } = await api.get(`/contacts?${params.toString()}`);
      return data;
    },
    placeholderData: (previousData) => previousData,
  });
}

export function useContact(contactId) {
  return useQuery({
    queryKey: contactKeys.detail(contactId),
    queryFn: async () => {
      const { data } = await api.get(`/contacts/${contactId}`);
      return data;
    },
    enabled: !!contactId,
  });
}