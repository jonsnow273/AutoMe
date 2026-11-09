import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../utils/api';

export const platformKeys = {
  all: ['platforms'],
  lists: () => [...platformKeys.all, 'list'],
  list: () => [...platformKeys.lists()],
  detail: (id) => [...platformKeys.all, 'detail', id],
};

export function usePlatforms() {
  return useQuery({
    queryKey: platformKeys.list(),
    queryFn: async () => {
      const { data } = await api.get('/platforms');
      return data;
    },
  });
}

export function usePlatform(platformId) {
  return useQuery({
    queryKey: platformKeys.detail(platformId),
    queryFn: async () => {
      const { data } = await api.get(`/platforms/${platformId}/status`);
      return data;
    },
    enabled: !!platformId,
  });
}

export function useConnectDiscord() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data) => {
      const { data: res } = await api.post('/platforms/discord/connect', data);
      return res;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: platformKeys.lists() });
    },
  });
}

export function useDisconnectPlatform() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (platformId) => {
      await api.delete(`/platforms/${platformId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: platformKeys.lists() });
    },
  });
}

export function useRestartPlatform() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (platformId) => {
      await api.post(`/platforms/${platformId}/restart`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: platformKeys.lists() });
    },
  });
}