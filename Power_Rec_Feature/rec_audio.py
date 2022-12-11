import sounddevice as sd


duration = 60
fs = 44100
print(sd.query_devices())

myrecording = sd.rec(int(duration*fs), samplerate=fs,channels=1)

sd.wait()
sf.write("test_rec.wav",date=myrecording,samplerate=1000)