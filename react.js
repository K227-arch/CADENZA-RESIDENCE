// Ensure this script runs after the LivekitClient library is loaded via CDN

document.addEventListener('DOMContentLoaded', () => {
    const startButton = document.getElementById('startAgentButton');
    const agentAudioElement = document.getElementById('agentAudio');
    const statusDisplay = document.getElementById('statusDisplay');

    let room = null; // Declare room outside to make it accessible

    // Configuration
    const TOKEN_SERVER_URL = 'http://localhost:8080/get-token'; // Your Token Server URL
    const LIVEKIT_ROOM_NAME = 'your-agent-room'; // Must match your Python agent's room name
    const PARTICIPANT_NAME = '3dvista-user-' + Math.floor(Math.random() * 1000); // Unique name for this user

    // Function to fetch the token from your Token Server
    async function fetchLiveKitToken() {
        try {
            statusDisplay.textContent = "Fetching access token...";
            const response = await fetch(TOKEN_SERVER_URL, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ roomName: LIVEKIT_ROOM_NAME, participantName: PARTICIPANT_NAME })
            });
            const data = await response.json();
            if (data.token && data.url) {
                statusDisplay.textContent = "Token fetched. Connecting to LiveKit...";
                return { token: data.token, url: data.url };
            } else {
                throw new Error("Invalid token data received");
            }
        } catch (error) {
            console.error('Error fetching token:', error);
            statusDisplay.textContent = `Error: ${error.message}. Is Token Server running?`;
            return null;
        }
    }

    // Function to connect to LiveKit and start audio
    async function connectToLiveKit() {
        const tokenData = await fetchLiveKitToken();
        if (!tokenData) return;

        const { token, url } = tokenData;

        // Create a new LiveKit Room instance
        room = new LivekitClient.Room();

        // Set up event listeners
        room.on(LivekitClient.RoomEvent.Connected, async () => {
            console.log('Connected to LiveKit room:', room.name);
            statusDisplay.textContent = "Connected to AI. Speaking...";

            // Auto-play audio requires user gesture. This attempts it.
            try {
                await room.startAudio(); // This needs to be triggered by user interaction
                console.log("Audio playback started automatically.");
            } catch (error) {
                console.warn("Autoplay blocked. User interaction needed to start audio.", error);
                statusDisplay.textContent = "Click anywhere to enable AI's voice.";
                // You might want to add an overlay or message instructing the user to click
                document.body.addEventListener('click', () => {
                    if (!room.canPlaybackAudio) {
                        room.startAudio();
                        statusDisplay.textContent = "Connected. Speak to the AI.";
                    }
                }, { once: true }); // Only listen for one click
            }

            // Enable local microphone
            try {
                await room.localParticipant.setMicrophoneEnabled(true);
                console.log("Microphone enabled.");
                statusDisplay.textContent = "Connected. Speak to the AI.";
            } catch (error) {
                console.error("Failed to enable microphone:", error);
                statusDisplay.textContent = `Error: Microphone access denied.`;
            }
        })
        .on(LivekitClient.RoomEvent.Disconnected, (reason) => {
            console.log('Disconnected from room:', reason);
            statusDisplay.textContent = `Disconnected: ${reason}.`;
            room = null;
        })
        .on(LivekitClient.RoomEvent.TrackSubscribed, (track, publication, participant) => {
            // Check if this is the AI agent's audio track
            // You might need to know your agent's identity (e.g., "ai-agent")
            // This is just an example; your agent's identity might be based on its `identity` in RoomInputOptions
            if (participant.identity.includes('agent') && track.kind === LivekitClient.Track.Kind.Audio) {
                console.log('Agent audio track subscribed:', participant.identity);
                // Attach the audio track to your audio element
                track.attach(agentAudioElement);
            }
        })
        .on(LivekitClient.RoomEvent.ActiveSpeakersChanged, (speakers) => {
            const agentSpeaking = speakers.some(s => s.identity.includes('agent'));
            if (agentSpeaking) {
                statusDisplay.textContent = "AI is speaking...";
            } else if (room && room.connectionState === LivekitClient.ConnectionState.Connected) {
                statusDisplay.textContent = "Connected. Speak to the AI.";
            }
        })
        // Add more event listeners for data messages (e.g., transcriptions from agent)
        .on(LivekitClient.RoomEvent.DataReceived, (payload, participant) => {
            try {
                const data = JSON.parse(new TextDecoder().decode(payload));
                if (data.type === 'transcription' && participant.identity === room.localParticipant.identity) {
                    // Display user's own transcription feedback if your agent sends it
                    // statusDisplay.textContent = `You: ${data.text}`;
                }
            } catch (e) {
                console.warn("Failed to parse data message:", e);
            }
        });

        // Connect to the room
        try {
            await room.connect(url, token);
        } catch (error) {
            console.error('Failed to connect to LiveKit room:', error);
            statusDisplay.textContent = `Failed to connect: ${error.message}.`;
        }
    }

    startButton.addEventListener('click', connectToLiveKit);
});