const express = require('express');
const cors = require('cors');
const qrcode = require('qrcode');
const axios = require('axios');
const path = require('path');
const { Client, LocalAuth } = require('whatsapp-web.js');

const app = express();
const PORT = process.env.PORT || 3001;
const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

app.use(cors());
app.use(express.json());

// In-memory store of active WhatsApp sessions: userId -> SessionObject
const sessions = new Map();

/**
 * Get or initialize WhatsApp client for a user.
 */
function createWhatsAppClient(userId) {
  if (sessions.has(userId)) {
    return sessions.get(userId);
  }

  const sessionData = {
    userId,
    status: 'initializing', // 'initializing' | 'qr' | 'ready' | 'disconnected'
    qr: null,
    userInfo: null,
    client: null,
  };

  const client = new Client({
    authStrategy: new LocalAuth({
      dataPath: path.join(__dirname, 'sessions'),
      clientId: `user-${userId}`,
    }),
    puppeteer: {
      headless: true,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-accelerated-2d-canvas',
        '--no-first-run',
        '--no-zygote',
        '--disable-gpu',
      ],
    },
  });

  client.on('qr', async (qrString) => {
    try {
      const qrDataUrl = await qrcode.toDataURL(qrString);
      sessionData.status = 'qr';
      sessionData.qr = qrDataUrl;
      console.log(`[WhatsApp] New QR code generated for user ${userId}`);
    } catch (err) {
      console.error(`[WhatsApp] Failed to generate QR data URL for user ${userId}:`, err);
    }
  });

  client.on('ready', async () => {
    sessionData.status = 'ready';
    sessionData.qr = null;
    const info = client.info;
    sessionData.userInfo = {
      phone: info ? info.wid.user : null,
      name: info ? info.pushname : null,
    };
    console.log(`[WhatsApp] Client is ready for user ${userId} (${sessionData.userInfo.phone})`);

    // Notify FastAPI backend
    try {
      await axios.post(`${BACKEND_URL}/platforms/whatsapp/webhook/ready`, {
        userId,
        phone: sessionData.userInfo.phone,
        name: sessionData.userInfo.name,
      });
    } catch (err) {
      console.error(`[WhatsApp] Failed to notify backend on ready: ${err.message}`);
    }
  });

  client.on('authenticated', () => {
    console.log(`[WhatsApp] Authenticated for user ${userId}`);
    sessionData.status = 'authenticated';
  });

  client.on('auth_failure', (msg) => {
    console.error(`[WhatsApp] Auth failure for user ${userId}:`, msg);
    sessionData.status = 'disconnected';
    sessionData.qr = null;
  });

  client.on('disconnected', (reason) => {
    console.log(`[WhatsApp] Disconnected for user ${userId}:`, reason);
    sessionData.status = 'disconnected';
    sessionData.qr = null;
    sessionData.userInfo = null;
  });

  client.on('message', async (msg) => {
    try {
      // Ignore status broadcast & group chats (only 1-on-1 DMs)
      if (msg.from === 'status@broadcast' || !msg.from.endsWith('@c.us')) {
        return;
      }

      const contact = await msg.getContact();
      const contactName = contact.name || contact.pushname || msg.from.replace('@c.us', '');
      const avatarUrl = await contact.getProfilePicUrl().catch(() => null);

      console.log(`[WhatsApp] Incoming message for user ${userId} from ${contactName}: "${msg.body}"`);

      // Forward to FastAPI backend
      const res = await axios.post(`${BACKEND_URL}/platforms/whatsapp/webhook/message`, {
        userId,
        from: msg.from,
        phone: msg.from.replace('@c.us', ''),
        name: contactName,
        avatarUrl: avatarUrl || null,
        messageId: msg.id.id,
        content: msg.body || '[Media/Attachment]',
        timestamp: msg.timestamp,
      });

      // If backend requested an auto-reply
      if (res.data && res.data.autoReply && res.data.replyText) {
        const replyText = res.data.replyText;
        const readDelay = 3500 + Math.random() * 2500; // 3.5 to 6s pause
        const typingDuration = Math.max(3000, Math.min(7500, replyText.length * 80 + Math.random() * 1500)); // 3 to 7.5s typing

        setTimeout(async () => {
          try {
            const chat = await msg.getChat();
            await chat.sendStateTyping();
            setTimeout(async () => {
              await client.sendMessage(msg.from, replyText);
              console.log(`[WhatsApp] Auto-reply sent to ${contactName} after typing: "${replyText}"`);
            }, typingDuration);
          } catch (replyErr) {
            console.error(`[WhatsApp] Failed to send auto-reply: ${replyErr.message}`);
          }
        }, readDelay);
      }
    } catch (err) {
      console.error(`[WhatsApp] Error processing message: ${err.message}`);
    }
  });

  sessionData.client = client;
  sessions.set(userId, sessionData);

  client.initialize().catch((err) => {
    console.error(`[WhatsApp] Client initialization error for user ${userId}:`, err);
    sessionData.status = 'disconnected';
  });

  return sessionData;
}

// ─── API Routes ──────────────────────────────────────────────

/**
 * Start/request WhatsApp session for user
 */
app.post('/session/start', (req, res) => {
  const { userId } = req.body;
  if (!userId) {
    return res.status(400).json({ error: 'userId is required' });
  }

  const session = createWhatsAppClient(userId);
  return res.json({
    userId,
    status: session.status,
    qr: session.qr,
    userInfo: session.userInfo,
  });
});

/**
 * Check session status & current QR code
 */
app.get('/session/status/:userId', (req, res) => {
  const userId = parseInt(req.params.userId, 10);
  const session = sessions.get(userId);

  if (!session) {
    return res.json({
      userId,
      status: 'disconnected',
      qr: null,
      userInfo: null,
    });
  }

  return res.json({
    userId,
    status: session.status,
    qr: session.qr,
    userInfo: session.userInfo,
  });
});

/**
 * Disconnect & destroy session
 */
app.post('/session/stop', async (req, res) => {
  const { userId } = req.body;
  const session = sessions.get(userId);

  if (session && session.client) {
    try {
      await session.client.destroy();
    } catch (err) {
      console.error(`Error destroying client for user ${userId}:`, err);
    }
    sessions.delete(userId);
  }

  return res.json({ message: 'Session stopped', userId });
});

/**
 * Send a message via user's WhatsApp session
 */
app.post('/message/send', async (req, res) => {
  const { userId, to, message } = req.body;
  if (!userId || !to || !message) {
    return res.status(400).json({ error: 'userId, to, and message are required' });
  }

  const session = sessions.get(userId);
  if (!session || session.status !== 'ready' || !session.client) {
    return res.status(400).json({ error: 'WhatsApp session not ready for user' });
  }

  try {
    const formattedTo = to.includes('@c.us') ? to : `${to}@c.us`;
    const chat = await session.client.getChatById(formattedTo).catch(() => null);
    if (chat) {
      await chat.sendStateTyping();
      await new Promise((r) => setTimeout(r, 1000));
    }
    const sent = await session.client.sendMessage(formattedTo, message);
    return res.json({
      success: true,
      messageId: sent.id.id,
      timestamp: sent.timestamp,
    });
  } catch (err) {
    console.error(`[WhatsApp] Failed to send message: ${err.message}`);
    return res.status(500).json({ error: err.message });
  }
});

app.get('/health', (req, res) => {
  res.json({ status: 'ok', activeSessions: sessions.size });
});

app.listen(PORT, () => {
  console.log(`AutoMe WhatsApp Service running on http://localhost:${PORT}`);
});
