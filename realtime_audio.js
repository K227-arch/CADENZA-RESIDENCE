// Real-time Audio Handler for Gemini Live API
class RealtimeAudioHandler {
    constructor() {
        this.websocket = null;
        this.mediaRecorder = null;
        this.audioContext = null;
        this.audioWorklet = null;
        this.isRecording = false;
        this.isConnected = false;
        this.audioQueue = [];
        this.isPlaying = false;
        
        // Real-time audio settings
        this.sampleRate = 16000;
        this.channels = 1;
        this.bufferSize = 1024; // Smaller buffer for lower latency
        
        this.initializeAudio();
    }
    
    async initializeAudio() {
        try {
            // Initialize audio context with low latency settings
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: this.sampleRate,
                latencyHint: 'interactive' // Optimize for low latency
            });
            
            console.log('🎵 Audio context initialized');
        } catch (error) {
            console.error('❌ Failed to initialize audio:', error);
        }
    }
    
    async connectWebSocket() {
        try {
            // Use the correct port for the real-time server
            this.websocket = new WebSocket('ws://localhost:8082/ws');
            
            this.websocket.onopen = () => {
                console.log('🔗 Connected to real-time server');
                this.isConnected = true;
                this.sendGreeting();
            };
            
            this.websocket.onmessage = (event) => {
                if (event.data instanceof ArrayBuffer) {
                    // Handle audio response
                    this.handleAudioResponse(event.data);
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
    
    sendGreeting() {
        if (this.websocket && this.isConnected) {
            this.websocket.send(JSON.stringify({
                type: 'ai_greeting',
                message: "Hello! I'm your AI assistant for the Cadenza Residence virtual tour. How can I help you today?"
            }));
        }
    }
    
    handleJsonMessage(message) {
        console.log('📨 Received message:', message);
        
        switch (message.type) {
            case 'greeting_complete':
                console.log('👋 Greeting completed:', message.message);
                break;
            case 'voice_status':
                console.log('🎤 Voice status:', message.status);
                break;
            case 'ai_turn_complete':
                console.log('✅ AI turn completed');
                break;
        }
    }
    
    async handleAudioResponse(audioData) {
        try {
            console.log(`🔊 Received ${audioData.byteLength} bytes of audio`);
            
            // Convert raw audio data to playable format
            const audioBuffer = await this.audioContext.decodeAudioData(audioData.slice(0));
            
            // Play immediately for real-time response
            this.playAudioBuffer(audioBuffer);
            
        } catch (error) {
            console.error('❌ Error handling audio response:', error);
            
            // Fallback: try to play as raw PCM
            try {
                await this.playRawPCM(audioData);
            } catch (fallbackError) {
                console.error('❌ Fallback audio playback failed:', fallbackError);
            }
        }
    }
    
    async playRawPCM(rawData) {
        // Convert raw PCM to AudioBuffer
        const samples = new Int16Array(rawData);
        const audioBuffer = this.audioContext.createBuffer(1, samples.length, 24000); // Gemini outputs at 24kHz
        const channelData = audioBuffer.getChannelData(0);
        
        // Convert Int16 to Float32
        for (let i = 0; i < samples.length; i++) {
            channelData[i] = samples[i] / 32768.0;
        }
        
        this.playAudioBuffer(audioBuffer);
    }
    
    playAudioBuffer(audioBuffer) {
        const source = this.audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(this.audioContext.destination);
        source.start();
        
        console.log(`🔊 Playing ${audioBuffer.duration.toFixed(2)}s of audio`);
    }
    
    async startRecording() {
        try {
            if (this.isRecording) return;
            
            console.log('🎤 Starting real-time recording...');
            
            // Get microphone access with low latency settings
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: this.sampleRate,
                    channelCount: this.channels,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    latency: 0.01 // 10ms latency
                }
            });
            
            // Create MediaRecorder for real-time streaming
            this.mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'audio/webm;codecs=pcm',
                audioBitsPerSecond: 16000
            });
            
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0 && this.websocket && this.isConnected) {
                    // Convert to ArrayBuffer and send immediately
                    event.data.arrayBuffer().then(buffer => {
                        this.websocket.send(buffer);
                        console.log(`🎤 Sent ${buffer.byteLength} bytes`);
                    });
                }
            };
            
            // Start recording with very small time slices for real-time streaming
            this.mediaRecorder.start(100); // 100ms chunks for low latency
            this.isRecording = true;
            
            // Notify server
            if (this.websocket && this.isConnected) {
                this.websocket.send(JSON.stringify({
                    type: 'start_realtime_voice'
                }));
            }
            
            console.log('✅ Real-time recording started');
            
        } catch (error) {
            console.error('❌ Failed to start recording:', error);
        }
    }
    
    stopRecording() {
        if (!this.isRecording) return;
        
        console.log('🔇 Stopping recording...');
        
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
        
        console.log('✅ Recording stopped');
    }
    
    // Public methods for integration
    async initialize() {
        await this.connectWebSocket();
        console.log('🚀 Real-time audio handler initialized');
    }
    
    async startVoiceChat() {
        if (this.audioContext.state === 'suspended') {
            await this.audioContext.resume();
        }
        await this.startRecording();
    }
    
    stopVoiceChat() {
        this.stopRecording();
    }
    
    disconnect() {
        this.stopRecording();
        if (this.websocket) {
            this.websocket.close();
        }
        if (this.audioContext) {
            this.audioContext.close();
        }
    }
}

// Global instance
window.realtimeAudio = new RealtimeAudioHandler();

// Auto-initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.realtimeAudio.initialize();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RealtimeAudioHandler;
}