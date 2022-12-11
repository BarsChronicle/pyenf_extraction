import sounddevice as sd
import soundfile as sf

duration = 60
fs = 44100
print(sd.query_devices())

sd.default.device = 2
myrecording = sd.rec(int(duration*fs), samplerate=fs,channels=1)

sd.wait()
sf.write("test_rec.wav",data=myrecording,samplerate=1000)