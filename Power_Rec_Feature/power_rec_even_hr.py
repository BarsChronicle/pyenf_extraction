import ntplib
import datetime
import time
import sounddevice as sd
import soundfile as sf
import sys
import os

folder_audio = "Power_Recordings/"

def power_rec(fs, duration, path): #buffer audio
    print(f"Enter recording: {duration} seconds")
    sd.default.device = 1
    buf_recording = sd.rec(int(duration * fs), samplerate=fs, channels=1) # buffer for the duration

    sd.wait()
    sf.write(folder_audio+path+".wav", data=buf_recording, samplerate=fs)
    #buf_recording = np.array(buf_recording).T.flatten() #resize to 1-D row vector 
    #write_data(path+".csv",buf_recording)
    #print(f'buf_recording: {buf_recording}')
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
            if (UTC_timestamp.microsecond < 10000): # ensure time isn't too close to next sec
                print(f'Synchronize at: {UTC_timestamp}')
                break
    
    time_until_record = 60 - UTC_timestamp.minute
    if (UTC_timestamp.hour % 2 == 0): # Next hour is odd, sleep over the odd hour block
        time_until_record += 60
    # Sleep some time, don't constantly use CPU resource for counting secs
    if (time_until_record > 10): # when there are more than 5 minutes until recording session
        print(f'Sleep {(time_until_record-10)*60} secs')
        time.sleep((time_until_record - 10)*60)
        restart()

    start_time = time.time()
    ## Offset to synchronized timestamp
    while(True): 
        end_time = time.time()

        if (int(end_time - start_time) >= 1): # count seconds to increment synchronized UTC timestamp
            UTC_ref = UTC_ref + (time.time() - start_time)
            start_time = time.time() #reset start time
            UTC_timestamp = datetime.datetime.utcfromtimestamp(UTC_ref)
            print(f'Sec: {UTC_timestamp.second} ->>>>>>>>> {UTC_timestamp}')
        
        if (UTC_timestamp.hour % 2 == 0 and UTC_timestamp.minute == 0 and UTC_timestamp.second == 0): # Fresh hour, start recording
            path = UTC_timestamp.strftime('%Y_%m_%d_%H_%M_%S')
            print(f'Recording Time: {UTC_timestamp}')
            power_rec(fs,duration, path)
            break #need to go back to 1st while loop somehow maybe nested loop, os.execv?

    restart()         

if __name__ == '__main__':
    main()