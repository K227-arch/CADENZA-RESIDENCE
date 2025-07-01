// token-server/index.js (or app.js)
require('dotenv').config();
const express = require('express');
const cors = require('cors');
const { AccessToken } = require('livekit-server-sdk');

const app = express();
app.use(cors()); // Enable CORS for frontend requests
app.use(express.json());

const LIVEKIT_API_KEY = process.env.LIVEKIT_API_KEY;
const LIVEKIT_API_SECRET = process.env.LIVEKIT_API_SECRET;
const LIVEKIT_URL = process.env.LIVEKIT_URL; // Your LiveKit server URL

if (!LIVEKIT_API_KEY || !LIVEKIT_API_SECRET || !LIVEKIT_URL) {
    console.error('LIVEKIT_API_KEY, LIVEKIT_API_SECRET, and LIVEKIT_URL must be set in .env');
    process.exit(1);
}

app.post('/get-token', (req, res) => {
    const { roomName, participantName } = req.body;

    if (!roomName || !participantName) {
        return res.status(400).send('roomName and participantName are required');
    }

    const at = new AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET, {
        identity: participantName,
        ttl: 6 * 60 * 60, // Token valid for 6 hours
    });
    at.addGrant({ roomJoin: true, room: roomName, canPublish: true, canSubscribe: true });

    const token = at.toJwt();
    res.json({ token, url: LIVEKIT_URL }); // Send back the token and LiveKit URL
});

const port = process.env.PORT || 8080;
app.listen(port, () => {
    console.log(`Token server listening on port ${port}`);
});