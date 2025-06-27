// Fixed audio playback for Gemini Live API raw PCM data
// This function correctly handles 16-bit PCM audio from Gemini (24kHz, mono)

async function playGeminiSpeech(audioData, audioContext) {
    try {
        console.log('🔊 Playing Gemini speech audio, data size:', audioData.byteLength || audioData.length);
        
        if (!audioContext) {
            audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 24000  // Gemini outputs at 24kHz
            });
            console.log('Created audio context for Gemini speech');
        }
        
        // Resume audio context if suspended
        if (audioContext.state === 'suspended') {
            await audioContext.resume();
        }
        
        // Convert raw PCM data from Gemini to AudioBuffer
        // Gemini sends 16-bit signed PCM at 24kHz, mono
        const pcmData = new Int16Array(audioData.buffer || audioData);
        const sampleRate = 24000; // Gemini's output sample rate
        const numSamples = pcmData.length;
        
        console.log(`🎵 Processing ${numSamples} samples at ${sampleRate}Hz`);
        
        // Create AudioBuffer manually for raw PCM data
        const audioBuffer = audioContext.createBuffer(1, numSamples, sampleRate);
        const channelData = audioBuffer.getChannelData(0);
        
        // Convert 16-bit signed integers to float32 (-1.0 to 1.0)
        for (let i = 0; i < numSamples; i++) {
            channelData[i] = pcmData[i] / 32768.0; // Convert to float32
        }
        
        // Create and play audio source
        const source = audioContext.createBufferSource();
        source.buffer = audioBuffer;
        
        // Add some gain control for better audio quality
        const gainNode = audioContext.createGain();
        gainNode.gain.value = 0.8; // Slightly reduce volume to prevent clipping
        
        source.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        // Set up event handlers
        return new Promise((resolve) => {
            source.onended = () => {
                console.log('✅ Gemini speech playback completed');
                resolve();
            };
            
            source.onerror = (error) => {
                console.error('❌ Speech playback error:', error);
                resolve();
            };
            
            // Start playback
            console.log(`��� Playing ${audioBuffer.duration.toFixed(2)}s of speech`);
            source.start();
        });
        
    } catch (error) {
        console.error('❌ Error playing Gemini speech:', error);
        throw error;
    }
}