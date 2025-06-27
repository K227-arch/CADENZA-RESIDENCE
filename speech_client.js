// Speech-enabled Audio Handler for Gemini Live API
class SpeechAudioHandler {
    constructor() {
        this.websocket = null;
        this.mediaRecorder = null;
        this.audioContext = null;
        this.isRecording = false;
        this.isConnected = false;
        this.isPlaying = false;
        
        // Audio settings optimized for speech
        this.sampleRate = 16000;
        this.outputSampleRate = 24000; // Gemini outputs at 24kHz
        this.channels = 1;
        
        this.initializeAudio();
    }
    
    async initializeAudio() {
        try {
            // Initialize audio context for speech playback
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: this.outputSampleRate,
                latencyHint: 'interactive'
            });
            
            console.log('🎵 Audio context initialized for speech');
        } catch (error) {
            console.error('❌ Failed to initialize audio:', error);
        }
    }
    
    async connectWebSocket() {
        try {
            // Connect to the speech-enabled server
            this.websocket = new WebSocket('ws://localhost:8083/ws');
            
            this.websocket.onopen = () => {
                console.log('🔗 Connected to speech server');
                this.isConnected = true;
                this.sendGreetingForSpeech();
            };
            
            this.websocket.onmessage = (event) => {
                if (event.data instanceof ArrayBuffer) {
                    // Handle speech audio response
                    this.handleSpeechResponse(event.data);
                } else {
                    // Handle JSON message
                    try {
                        const message = JSON.parse(event.data);
                        this.handleJsonMessage(message);
                    } catch (error) {
                        console.error('❌ Failed to parse message:', error);
                    }
                }
            };
            
            this.websocket.onclose = () => {
                console.log('🔌 WebSocket disconnected');
                this.isConnected = false;
            };
            
            this.websocket.onerror = (error) => {
                console.error('❌ WebSocket error:', error);
            };
            
        } catch (error) {
            console.error('❌ Failed to connect WebSocket:', error);
        }
    }
    
    sendGreetingForSpeech() {
        if (this.websocket && this.isConnected) {
            console.log('👋 Requesting speech greeting...');
            this.websocket.send(JSON.stringify({
                type: 'ai_greeting',
                message: "Hello! I'm your AI assistant for the Cadenza Residence virtual tour. How can I help you today?"
            }));
        }
    }
    
    handleJsonMessage(message) {
        console.log('📨 Received message:', message);
        
        switch (message.type) {
            case 'voice_status':
                console.log('🎤 Voice status:', message.status);
                break;
            case 'ai_turn_complete':
                console.log('✅ AI speech turn completed');
                this.isPlaying = false;
                break;
        }
    }
    
    async handleSpeechResponse(audioData) {
        try {
            console.log(`🔊 Received ${audioData.byteLength} bytes of speech audio`);
            this.isPlaying = true;
            
            // Method 1: Try to decode as standard audio format
            try {
                const audioBuffer = await this.audioContext.decodeAudioData(audioData.slice(0));
                this.playSpeechBuffer(audioBuffer);
                return;
            } catch (decodeError) {
                console.log('🔄 Standard decode failed, trying raw PCM...');
            }
            
            // Method 2: Handle as raw PCM data from Gemini
            await this.playRawSpeechPCM(audioData);
            
        } catch (error) {
            console.error('❌ Error handling speech response:', error);
            this.isPlaying = false;
        }
    }
    
    async playRawSpeechPCM(rawData) {
        try {
            // Convert raw PCM to AudioBuffer (Gemini outputs 24kHz, 16-bit, mono)
            const samples = new Int16Array(rawData);
            const audioBuffer = this.audioContext.createBuffer(1, samples.length, this.outputSampleRate);
            const channelData = audioBuffer.getChannelData(0);
            
            // Convert Int16 to Float32 for Web Audio API
            for (let i = 0; i < samples.length; i++) {
                channelData[i] = samples[i] / 32768.0;
            }
            
            this.playSpeechBuffer(audioBuffer);
            
        } catch (error) {
            console.error('❌ Error playing raw speech PCM:', error);
            this.isPlaying = false;
        }
    }
    
    playSpeechBuffer(audioBuffer) {
        try {
            const source = this.audioContext.createBufferSource();
            source.buffer = audioBuffer;
            
            // Add some audio processing for better speech quality
            const gainNode = this.audioContext.createGain();
            gainNode.gain.value = 1.0; // Adjust volume if needed
            
            source.connect(gainNode);
            gainNode.connect(this.audioContext.destination);
            
            source.onended = () => {
                console.log('🔊 Speech playback completed');
                this.isPlaying = false;
            };
            
            source.start();
            
            console.log(`🔊 Playing ${audioBuffer.duration.toFixed(2)}s of speech`);
            
        } catch (error) {
            console.error('❌ Error playing speech buffer:', error);
            this.isPlaying = false;
        }
    }
    
    async startSpeechRecording() {
        try {
            if (this.isRecording) return;
            
            console.log('🎤 Starting speech recording...');
            
            // Resume audio context if suspended
            if (this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
            }
            
            // Get microphone access optimized for speech
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: this.sampleRate,
                    channelCount: this.channels,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    latency: 0.01
                }
            });
            
            // Create MediaRecorder for speech
            this.mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'audio/webm;codecs=opus',
                audioBitsPerSecond: 16000
            });
            
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0 && this.websocket && this.isConnected) {
                    // Send audio data for speech processing
                    event.data.arrayBuffer().then(buffer => {
                        this.websocket.send(buffer);
                        console.log(`🎤 Sent ${buffer.byteLength} bytes for speech processing`);
                    });
                }
            };
            
            // Start recording with small chunks for responsive speech
            this.mediaRecorder.start(250); // 250ms chunks
            this.isRecording = true;
            
            // Notify server
            if (this.websocket && this.isConnected) {
                this.websocket.send(JSON.stringify({
                    type: 'start_realtime_voice'
                }));
            }
            
            console.log('✅ Speech recording started');
            
        } catch (error) {
            console.error('❌ Failed to start speech recording:', error);
        }
    }
    
    stopSpeechRecording() {
        if (!this.isRecording) return;
        
        console.log('🔇 Stopping speech recording...');
        
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
            this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
        }
        
        this.isRecording = false;
        
        // Notify server
        if (this.websocket && this.isConnected) {
            this.websocket.send(JSON.stringify({
                type: 'stop_realtime_voice'
            }));
        }
        
        console.log('✅ Speech recording stopped');
    }
    
    // Public methods
    async initialize() {
        await this.connectWebSocket();
        console.log('🚀 Speech audio handler initialized');
    }
    
    async startVoiceChat() {
        if (this.audioContext.state === 'suspended') {
            await this.audioContext.resume();
        }
        await this.startSpeechRecording();
    }
    
    stopVoiceChat() {
        this.stopSpeechRecording();
    }
    
    disconnect() {
        this.stopSpeechRecording();
        if (this.websocket) {
            this.websocket.close();
        }
        if (this.audioContext) {
            this.audioContext.close();
        }
    }
    
    // Test speech functionality
    async testSpeech() {
        if (this.websocket && this.isConnected) {
            console.log('🧪 Testing speech response...');
            this.websocket.send(JSON.stringify({
                type: 'ai_greeting',
                message: "Please say hello and introduce yourself as the Cadenza Residence tour assistant."
            }));
        }
    }
}

// Global instance for speech
window.speechAudio = new SpeechAudioHandler();

// Auto-initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.speechAudio.initialize();
    
    // Add test button for speech
    setTimeout(() => {
        const testButton = document.createElement('button');
        testButton.textContent = '🔊 Test Speech';
        testButton.style.position = 'fixed';
        testButton.style.top = '10px';
        testButton.style.right = '10px';
        testButton.style.zIndex = '9999';
        testButton.style.padding = '10px';
        testButton.style.backgroundColor = '#4CAF50';
        testButton.style.color = 'white';
        testButton.style.border = 'none';
        testButton.style.borderRadius = '5px';
        testButton.style.cursor = 'pointer';
        
        testButton.onclick = () => {
            window.speechAudio.testSpeech();
        };
        
        document.body.appendChild(testButton);
    }, 2000);
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SpeechAudioHandler;
}