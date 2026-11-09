import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import api from '../utils/api';
import { PLATFORMS } from '../utils/constants';
import PlatformCard from '../components/PlatformCard';

export default function ConnectPlatforms() {
  const navigate = useNavigate();
  const [platforms, setPlatforms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchPlatforms = async () => {
    try {
      const res = await api.get('/platforms');
      setPlatforms(res.data || []);
    } catch (err) {
      console.error('Failed to fetch platforms', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPlatforms();
  }, []);

  const handleConnect = async (platformId, payload) => {
    setActionLoading(true);
    try {
      if (platformId === 'discord') {
        await api.post('/platforms/discord/connect', payload);
        toast.success('Discord bot connected and running');
      } else {
        toast.error(`${platformId} connection coming in next phase`);
        return;
      }
      await fetchPlatforms();
    } catch (err) {
      console.error('Connect error:', err);
      const msg = err.response?.data?.detail || 'Failed to connect platform';
      toast.error(msg);
    } finally {
      setActionLoading(false);
    }
  };

  const handleDisconnect = async (platformTypeOrId) => {
    setActionLoading(true);
    try {
      // Find platform record if numeric id was passed, otherwise use platform type string directly
      const platformType = typeof platformTypeOrId === 'string'
        ? platformTypeOrId
        : platforms.find(p => p.id === platformTypeOrId)?.platform_type || 'discord';

      await api.post(`/platforms/disconnect-type/${platformType}`);
      toast.success(`${platformType.toUpperCase()} disconnected and removed`);
      await fetchPlatforms();
    } catch (err) {
      console.error('Disconnect error:', err);
      const msg = err.response?.data?.detail || 'Failed to disconnect';
      toast.error(msg);
    } finally {
      setActionLoading(false);
    }
  };

  const handleReconnect = async (platformId) => {
    setActionLoading(true);
    try {
      const record = getPlatformRecord(platformId);
      if (record?.id) {
        await api.post(`/platforms/${record.id}/restart`);
        toast.success(`${platformId.toUpperCase()} bot reconnected and running`);
      } else {
        await api.post('/platforms/discord/reconnect');
        toast.success('Discord bot reconnected and running');
      }
      await fetchPlatforms();
    } catch (err) {
      console.error('Reconnect error:', err);
      const msg = err.response?.data?.detail || 'Failed to reconnect bot';
      toast.error(msg);
      await fetchPlatforms();
    } finally {
      setActionLoading(false);
    }
  };

  const getPlatformRecord = (type) => {
    return platforms.find((p) => p.platform_type === type);
  };

  return (
    <div className="min-h-screen bg-dark-900 text-gray-100 p-6 lg:p-12">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl lg:text-3xl font-bold text-white tracking-tight">
              Connected Platforms
            </h1>
            <p className="text-sm text-gray-400 mt-1">
              Link your social accounts so AutoMe can monitor and reply to your messages.
            </p>
          </div>
          <button
            onClick={() => navigate('/inbox')}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium bg-dark-800 hover:bg-dark-700 border border-dark-600 transition-colors"
          >
            ← Back to Inbox
          </button>
        </div>

        {/* Platform Cards */}
        {loading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-28 bg-dark-800 rounded-2xl animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="space-y-4">
            <PlatformCard
              platform={PLATFORMS.discord}
              platformRecord={getPlatformRecord('discord')}
              onConnect={handleConnect}
              onDisconnect={handleDisconnect}
              onReconnect={handleReconnect}
              loading={actionLoading}
            />

            <PlatformCard
              platform={PLATFORMS.whatsapp}
              platformRecord={getPlatformRecord('whatsapp')}
              onConnect={() => toast('WhatsApp connection coming in Phase 4')}
              onDisconnect={handleDisconnect}
              loading={actionLoading}
            />

            <PlatformCard
              platform={PLATFORMS.instagram}
              platformRecord={getPlatformRecord('instagram')}
              onConnect={() => toast('Instagram connection coming in Phase 3')}
              onDisconnect={handleDisconnect}
              loading={actionLoading}
            />
          </div>
        )}
      </div>
    </div>
  );
}
