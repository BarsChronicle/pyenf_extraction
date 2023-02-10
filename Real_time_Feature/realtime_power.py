import ntplib
import datetime
import time
import threading
import sounddevice as sd
import numpy as np
import pyenf

buf_recording = [] #global variables for each thread to return
estimated_ENF = []

def proc1_estimate_ENF(enf_signal, fs, nfft, frame_size, overlap):
    print("Enter estimate thread")
    global estimated_ENF
    enf_signal_object = pyenf.pyENF(signal0=enf_signal, fs=fs, nominal=60, harmonic_multiples=1, duration=0.1,
                                    strip_index=0, frame_size_secs=frame_size, nfft=nfft, overlap_amount_secs=overlap)
    enf_spectro_strip, enf_frequency_support = enf_signal_object.compute_spectrogam_strips()
    enf_weights = enf_signal_object.compute_combining_weights_from_harmonics()
    enf_OurStripCell, enf_initial_frequency = enf_signal_object.compute_combined_spectrum(enf_spectro_strip,
                                                                                          enf_weights,
                                                                                          enf_frequency_support)
    estimated_ENF = enf_signal_object.compute_ENF_from_combined_strip(enf_OurStripCell, enf_initial_frequency)
    estimated_ENF = np.array(estimated_ENF).T.flatten()
    #print(estimated_ENF)
    print("Exit estimate thread")

def proc2_buffer_next(fs, duration): #buffer audio
    print(f"Enter buffer thread: {duration} seconds")
    global buf_recording
    sd.default.device = 1
    buf_recording = sd.rec(int(duration * fs), samplerate=fs, channels=1) # buffer 5 seconds

    sd.wait()
    buf_recording = np.array(buf_recording).T.flatten() #resize to 1-D row vector 
    print("Exit buffer thread")

def write_data(csv_filename, data): # write data to csv file
    counter = 0
    folderpath = "Junk_Data/"
    with open(csv_filename,'w') as file:
        for item in data:
            x = str(counter)+","+str(item)+"\n" # Counter, ENF value
            file.write(x)
            counter += 1

def main():
    #parameters for the STFT algorithm
    init_duration = 62
    duration = 6
    fs = 1000 # downsampling frequency
    nfft = 8192
    frame_size = 2  # change it to 6 for videos with large length recording
    overlap = 0

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
        
        if (UTC_timestamp.hour == 19 and UTC_timestamp.minute == 25 and UTC_timestamp.second == 0):
            break 

    print("Started Recording: ")
    start = time.perf_counter()

    # Buffer 1st 60 seconds
    proc2_buffer_next(fs, init_duration)
    myrecording = np.array(buf_recording)
    ENF_vector = []
    count_loop = 0

    while (len(ENF_vector) < 1800):  # replace with True
        print("###################################################################")
        t1 = threading.Thread(target=proc1_estimate_ENF, args=(myrecording, fs, nfft, frame_size, overlap))
        t2 = threading.Thread(target=proc2_buffer_next, args=(fs, duration))
        
        print("Start Thread")

        t1.start()
        t2.start()

        t1.join()
        t2.join()
        print("Exit Thread")
        
        # power_ENF = estimate.value
        # myrecording5 = buffer.value   [duration*fs:]    extend
        # original60 
        # overlap_55 = original60[duration*fs:] -->> throw away past 5 sec
        # new60 = overlap.extend(myrecording5)  -->> appends new 5 sec

        #myrecording = myrecording[(init_duration-62)*fs:] #keep latest 62 seconds

        if (len(ENF_vector) == 0): #Append First 60 second
            myrecording = myrecording[(init_duration-2)*fs:] #throw away 1-60, keep 61, 62 sec.
            ENF_vector = np.array(estimated_ENF[:int(init_duration/frame_size)-1])
    
        else:
            myrecording = myrecording[duration*fs:] # keep last 2 seconds that did yielded junk data
            ENF_vector = np.append(ENF_vector, estimated_ENF[:int(duration/frame_size)]) #append new seconds

        myrecording = np.append(myrecording, buf_recording) #append new 6 sec
        #print(ENF_vector)
        
        count_loop += 1
    
    finish = time.perf_counter()
    print(f"Finished in {round(finish-start,2)} seconds(s)")

    write_data("RealtimeENF.csv", ENF_vector[:1800])

if __name__ == '__main__':
    main()