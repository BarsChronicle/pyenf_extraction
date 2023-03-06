import sounddevice as sd
import numpy as np
import time
import datetime
import threading
import pyenf
import ntplib

ENF_vector = []
buffer = []

def estimate_ENF(enf_signal, fs, nfft, frame_size, overlap):
    enf_signal_object = pyenf.pyENF(signal0=enf_signal, fs=fs, nominal=60, harmonic_multiples=1, duration=0.1,
                                    strip_index=0, frame_size_secs=frame_size, nfft=nfft, overlap_amount_secs=overlap)
    enf_spectro_strip, enf_frequency_support = enf_signal_object.compute_spectrogam_strips()
    enf_weights = enf_signal_object.compute_combining_weights_from_harmonics()
    enf_OurStripCell, enf_initial_frequency = enf_signal_object.compute_combined_spectrum(enf_spectro_strip,
                                                                                          enf_weights,
                                                                                          enf_frequency_support)
    ENF = enf_signal_object.compute_ENF_from_combined_strip(enf_OurStripCell, enf_initial_frequency)
    ENF = np.array(ENF).T.flatten()
    return ENF

def init_rec(fs, duration, device_name): #buffer audio
    print(f"Enter recording: {duration} seconds")
    global buffer
    sd.default.device = device_name
    buf_recording = sd.rec(int(duration * fs), samplerate=fs, channels=1) # buffer for the duration

    sd.wait()
    buf_recording = np.array(buf_recording).T.flatten() #resize to 1-D row vector 
    buffer = buf_recording

def write_data(csv_filename, data): # write data to csv file
    counter = 0
    #folderpath = "Junk_Data/"
    with open(csv_filename,'w') as file:
        for item in data:
            x = str(counter)+","+str(item)+"\n" # Counter, ENF value
            file.write(x)
            counter += 1

def sync_wait():
    ntpc = ntplib.NTPClient()
    host = 'pool.ntp.org'
    UTC_ref = time.time()
    
    UTC_hour = 7
    UTC_min = 0
    UTC_sec = 0

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
        
        if (UTC_timestamp.minute == UTC_min and UTC_timestamp.second == UTC_sec):
            break

def callback(indata, frames, time, status): # callback function to add recorded audio to a buffer and process that buffer
    global buffer
    buffer = np.append(buffer,indata.flatten()) # add new recording to buffer

    if len(buffer) > 20000: # estimate from 20 secs recording
        buffer = buffer[6000:] # chop off first 6 secs from previous buffer
        flag = 1
    else: # 1st buffer
        flag = 0

    #print(f'size: {len(buffer)} buf1: {buffer}')
    threading.Thread(target=process_recording,args=(buffer,flag)).start() # leave processing to thread

def process_recording(buffer,flag):  
    global ENF_vector
    fs = 1000
    nfft = 8192
    frame_size = 2
    overlap = 0
    ENF = estimate_ENF(buffer, fs, nfft, frame_size, overlap)
    
    # Following configurations only for frame_size=2
    real_data_lim = -3 
    if flag == 1: # Susequent buffer chop repeating 1st 6 ENF data
        ENF = ENF[6:]

    # trim junk tailend
    ENF = ENF[:real_data_lim]
    ENF_vector = np.append(ENF_vector, ENF)

    #timestamp = time.strftime('%H_%M_%S', time.localtime())
    #filename = f"recording_{timestamp}.csv"
    #write_data(filename,ENF)
    
def main():
    # set up the recording parameters
    init_duration = 14
    buffer_duration = 6 # in seconds
    fs = 1000
    frame_cnt = int(fs * buffer_duration)
    device_name = 'Microphone (3- USB Audio Device'

    # Blocks the program until synchronized
    sync_wait()

    # Buffer 1st few seconds
    init_rec(fs,init_duration,device_name)

    # buffer stream
    with sd.InputStream(device=device_name, callback=callback, channels=1,blocksize=frame_cnt, samplerate=fs):
        while True:
            pass
    
    #write_data("realtime_ENF.csv", ENF_vector)

if __name__ == '__main__':
    main()
