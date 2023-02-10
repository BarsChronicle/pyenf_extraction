import sounddevice as sd1
import sounddevice as sd2
import librosa
import soundfile as sf


duration = 8
fs = 1000

print("Started Recording")
print(sd1.query_devices())

sd1.default.device = 1;#Laptop mic
myrecording = sd1.rec(int(duration * fs), samplerate=fs, channels=1) # buffer 5 seconds

sd1.wait()
#print(myrecording)
print("Done recording")
sf.write("power_wall.wav", data=myrecording, samplerate=fs)
"""
counter = 0
csv_filename = "testaudio.csv"
with open(csv_filename,'w') as file:
    for each_enf in myrecording:
        x = str(counter)+","+str(each_enf)+"\n" # Counter, ENF value
        file.write(x)
        counter = counter+1

#######################################################################################
print("Started Recording")

sd2.default.device = 2; #select device to record, RAZER
myrecording = sd2.rec(int(duration * fs), samplerate=fs, channels=1) # buffer 5 seconds

sd2.wait()
print(myrecording)
print("Done recording")
sf.write("test_rec2.wav", data=myrecording, samplerate=fs)
"""