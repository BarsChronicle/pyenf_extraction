import ntplib
import datetime
import time
import sounddevice as sd
import soundfile as sf
import sys
import os

def power_rec(fs, duration): #buffer audio
    print(f"Enter recording: {duration} seconds")
    sd.default.device = 1
    buf_recording = sd.rec(int(duration * fs), samplerate=fs, channels=1) # buffer for the duration

    sd.wait()
    sf.write("Continuous_hour.wav", data=buf_recording, samplerate=fs)
    print("Exit recording")

def restart():
    print("argv: ", sys.argv)
    print("sys executable: ", sys.executable)
    print("Restart now!")
    os.execv(sys.executable, ['python'] + sys.argv)

def main():
    #parameters for the STFT algorithm
    dur_minute = 60
    duration = (60*dur_minute) + 10
    fs = 1000 # downsampling frequency

    ntpc = ntplib.NTPClient()
    host = 'pool.ntp.org'
    #host = '1.us.pool.ntp.org'
    UTC_ref = time.time()
    
    ## Synchronize with NTP
    while(True): 
        try:
            UTC_ref = ntpc.request(host).tx_time

        except ntplib.NTPException:
            print(f'Ntp_Exception thrown, Last:{datetime.datetime.utcfromtimestamp(UTC_ref)}')
        else:
            UTC_timestamp = datetime.datetime.utcfromtimestamp(UTC_ref)
            print(f'Synchronize at: {UTC_timestamp}')
            break

    start_time = time.time()

    ## Offset to synchronized timestamp
    while(True): 
        end_time = time.time()

        if (end_time-start_time >= .01): # count time to increment synchronized UTC timestamp
            UTC_ref = UTC_ref + (time.time() - start_time)
            start_time = time.time() #reset start time
            UTC_timestamp = datetime.datetime.utcfromtimestamp(UTC_ref)
            print(f'Sec: {UTC_timestamp.second} ->>>>>>>>> {UTC_timestamp}')
        
        if (UTC_timestamp.hour == 19 and UTC_timestamp.minute == 25 and UTC_timestamp.second == 0): # Fresh hour, start recording
            power_rec(fs,duration)
            break #need to go back to 1st while loop somehow maybe nested loop, os.execv?         

if __name__ == '__main__':
    main()