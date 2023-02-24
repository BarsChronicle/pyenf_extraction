import ntplib
import datetime
import time
import concurrent.futures
import sounddevice as sd
import numpy as np
import pyenf

def proc1_estimate_ENF(enf_signal, fs, nfft, frame_size, overlap):
    #print("Enter estimate thread")
    enf_signal_object = pyenf.pyENF(signal0=enf_signal, fs=fs, nominal=60, harmonic_multiples=1, duration=0.1,
                                    strip_index=0, frame_size_secs=frame_size, nfft=nfft, overlap_amount_secs=overlap)
    enf_spectro_strip, enf_frequency_support = enf_signal_object.compute_spectrogam_strips()
    enf_weights = enf_signal_object.compute_combining_weights_from_harmonics()
    enf_OurStripCell, enf_initial_frequency = enf_signal_object.compute_combined_spectrum(enf_spectro_strip,
                                                                                          enf_weights,
                                                                                          enf_frequency_support)
    estimated_ENF = enf_signal_object.compute_ENF_from_combined_strip(enf_OurStripCell, enf_initial_frequency)
    estimated_ENF = np.array(estimated_ENF).T.flatten()
    return estimated_ENF
    #print("Exit estimate thread")

def proc2_buffer_next(fs, duration): #buffer audio
    print(f"Enter buffer thread: {duration} seconds")
    sd.default.device = 1
    buf_recording = sd.rec(int(duration * fs), samplerate=fs, channels=1) # buffer 5 seconds

    sd.wait()
    buf_recording = np.array(buf_recording).T.flatten() #resize to 1-D row vector
    return buf_recording 
    #print("Exit buffer thread")

def write_data(csv_filename, data): # write data to csv file
    counter = 0
    with open(csv_filename,'w') as file:
        for item in data:
            x = str(counter)+","+str(item)+"\n" # Counter, ENF value
            file.write(x)
            counter += 1

def main():
    buf_recording = [] #return values from threads
    estimated_ENF = []

    #parameters for the STFT algorithm
    init_duration = 62
    duration = 6
    fs = 1000 # downsampling frequency
    nfft = 8192
    frame_size = 2  # change it to 6 for videos with large length recording
    overlap = 0
    
    # parameters for time sync
    UTC_hour = 2
    UTC_min = 38
    UTC_sec = 0
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
        
        if (UTC_timestamp.hour == UTC_hour and UTC_timestamp.minute == UTC_min and UTC_timestamp.second == UTC_sec): # set specific hr,min,sec to start recording
            break 
    
    print("Started Recording: ")
    start = time.perf_counter()

    # Buffer 1st 62 seconds
    buf_recording = proc2_buffer_next(fs, init_duration)
    myrecording = np.array(buf_recording)
    ENF_vector = []
    count_loop = 0

    while (len(ENF_vector) < 1800):  # replace with True
        print("###################################################################")
        #print("Start Thread")
        with concurrent.futures.ThreadPoolExecutor() as executor:
            f1 = executor.submit(proc1_estimate_ENF, myrecording, fs, nfft, frame_size, overlap) #execute thread and send its parameters 
            f2 = executor.submit(proc2_buffer_next, fs, duration)
            
            estimated_ENF = f1.result() # get return value from thread function
            buf_recording = f2.result()
        #print("Exit Thread")

        #print(f'Estimate: {estimated_ENF}')
        if (len(ENF_vector) == 0): #Append First 60 second
            ENF_vector = np.array(estimated_ENF[:int(init_duration/frame_size)-1])
        else:
            ENF_vector = np.append(ENF_vector, estimated_ENF[-6:-3]) #append new seconds
        #print(f'ENF: {ENF_vector}')
        myrecording = np.append(myrecording, buf_recording) #append new 6 sec
        myrecording = myrecording[(-init_duration*fs):] # keep last 62 seconds
        #print(ENF_vector)
        
        count_loop += 1
    
    finish = time.perf_counter()
    print(f"Finished in {round(finish-start,2)} seconds(s)")

    write_data("PCB.csv", ENF_vector)

if __name__ == '__main__':
    main()