## Processing might lag behind recording
import sounddevice as sd
import soundfile as sf
import numpy as np
import time
import threading
import pyenf

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

def write_data(csv_filename, data): # write data to csv file
    counter = 0
    #folderpath = "Junk_Data/"
    with open(csv_filename,'w') as file:
        for item in data:
            x = str(counter)+","+str(item)+"\n" # Counter, ENF value
            file.write(x)
            counter += 1

def callback(indata, frames, time, status): # callback function to add recorded audio to a buffer and process that buffer
    if status:
        print(status)

    global buffer
    if len(buffer) == 0:
        buffer = indata.flatten()
        flag = 0
    elif len(buffer) >= 16000: # always estiamte from 16 secs recording
        buffer = buffer[8000:] # chop off first 8 secs from previous buffer
        buffer = np.append(buffer,indata.flatten()) # add new recording to buffer
        flag = 2
    else: # second buffer
        buffer = np.append(buffer,indata.flatten()) 
        flag = 1
    
    print(f'size: {len(buffer)} buf1: {buffer}')

    threading.Thread(target=process_recording,args=(buffer,flag)).start() # leave processing to thread

def process_recording(buffer, flag):
    timestamp = time.strftime('%H_%M_%S', time.localtime())
    filename = f"recording_{timestamp}.csv"
    
    fs = 1000
    nfft = 8192
    frame_size = 2
    overlap = 0
    ENF = estimate_ENF(buffer, fs, nfft, frame_size, overlap)

    real_data_lim = -3
    if flag == 1: # Second buffer chop 1st 3 ENF data
        ENF = ENF[3:]
    elif flag == 2: # Susequent buffer chop repeating 1st 2 ENF data
        ENF = ENF[2:]

    # trim junk tailend
    ENF = ENF[:real_data_lim]

    write_data(filename,ENF)
    
    global ENF_vector
    ENF_vector = np.append(ENF_vector, ENF)

# set up the recording parameters
buffer_duration = 8 # in seconds
fs = 1000
frame_cnt = int(fs * buffer_duration)
device_name = 'Microphone (3- USB Audio Device'

# start the recording
with sd.InputStream(device=device_name, callback=callback, channels=1,blocksize=frame_cnt, samplerate=fs):
    while True:
        pass
