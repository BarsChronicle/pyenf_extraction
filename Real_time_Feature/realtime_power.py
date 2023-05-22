import sounddevice as sd
import numpy as np
import time
import datetime
import threading
import pyenf
import ntplib
import sys
import os

# Set up the recording parameters
init_duration = 8
buffer_duration = 12 # in seconds
device_name = 1

# ENF function parameters
fs = 1000
nfft = 8192
frame_size = 2
overlap = 0

# Output & Time sync parameter
folderpath = 'ENF_Data' #change to absolute path of folder in computing hardware
UTC_timestamp = ''

# Recording buffers
ENF_vector = []
buffer = []

# Define mutex
mutex_ENF = threading.Lock()
mutex_buf = threading.Lock()

def estimate_ENF(enf_signal):
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

def init_rec(): #buffer audio
    print(f"Enter recording: {init_duration} seconds")
    global buffer
    sd.default.device = device_name
    buf_recording = sd.rec(int(init_duration * fs), samplerate=fs, channels=1) # buffer for the duration

    sd.wait()
    buf_recording = np.array(buf_recording).T.flatten() #resize to 1-D row vector 
    buffer = buf_recording

def write_data(csv_filename, data): # write data to csv file
    counter = 0
    with open(csv_filename,'w') as file:
        for item in data:
            x = str(counter)+","+str(item)+"\n" # Counter, ENF value
            file.write(x)
            counter += 1

def restart():
    print("argv: ", sys.argv)
    print("sys executable: ", sys.executable)
    print("Restart now!")
    os.execv(sys.executable, ['python'] + sys.argv)

def sync_wait():
    ntpc = ntplib.NTPClient()
    host = 'pool.ntp.org'
    global UTC_timestamp
    UTC_ref = time.time()
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
    
    time_until_record = 60 - UTC_timestamp.minute
    time_offset = 3

    # Sleep some time, don't constantly use CPU resource for counting secs
    if (time_until_record > time_offset): # when there are more than 3 minutes until recording session
        print(f'Sleep {(time_until_record - time_offset)*60} secs')
        time.sleep((time_until_record - time_offset)*60)
        restart()

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
    if status:
        print(status)

    mutex_buf.acquire()
    global buffer
    buffer = np.append(buffer,indata.flatten()) # add new recording to buffer

    if len(buffer) > ((init_duration+buffer_duration)*fs): # estimate from 20 secs recording
        buffer = buffer[(buffer_duration*fs):] # chop off first 12 secs from previous buffer
        flag = 1
    else: # 1st buffer
        flag = 0
    buf_rec = buffer
    mutex_buf.release()

    threading.Thread(target=process_recording,args=(buf_rec,flag)).start() # leave processing to thread

def process_recording(buf_rec,flag):  
    mutex_ENF.acquire()
    global ENF_vector
    ENF = estimate_ENF(buf_rec)
    """
    # Following configurations only for frame_size=2, buffer_sec=6
    real_data_lim = -3 
    if flag == 1: # Susequent buffer chop repeating 1st 6 ENF data
        ENF = ENF[6:]
    """
    # Following configurations only for frame_size=2, buffer_sec=12
    real_data_lim = -3 
    if flag == 1: # Susequent buffer chop repeating 1st 6 ENF data
        ENF = ENF[3:]
    
    # trim junk tailend
    ENF = ENF[:real_data_lim]
    ENF_vector = np.append(ENF_vector, ENF)

    if (len(ENF_vector) >= 1800):
        export_ENF = ENF_vector[:1800]
        ENF_vector = ENF_vector[1800:] # push out ENF from the 1st hour
        mutex_ENF.release()
        threading.Thread(target=export_data,args=(export_ENF,)).start() # leave processing to thread
    else:
        mutex_ENF.release()

def export_data(data):
    global UTC_timestamp
    timestamp = UTC_timestamp.strftime('UTC_%Y_%m_%d_%H_%M_%S')
    filename = f"Power_Recordings/{timestamp}.csv"
    write_data(filename,data)
    UTC_timestamp = UTC_timestamp + datetime.timedelta(hours=1) # increment hour

def main():
    # Blocks the program until synchronized
    sync_wait()

    # Buffer 1st few seconds
    init_rec()

    frame_cnt = int(fs * buffer_duration)
    # buffer stream
    with sd.InputStream(device=device_name, callback=callback, channels=1,blocksize=frame_cnt, samplerate=fs):
        while True:
            pass

if __name__ == '__main__':
    main()