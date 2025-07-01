# check_audio.py
import sounddevice as sd

print("Listing all available audio devices:\n")
print(sd.query_devices())