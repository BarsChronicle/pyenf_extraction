# Demonstrates how the real-time progrom works
import sounddevice as sd
import soundfile as sf
import numpy as np
import time
import threading
import pyenf

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

    # buffer.append(indata.copy())
    global buffer

    if len(buffer) == 0:
        buffer = indata.flatten()
    else:
        buffer = np.append(buffer,indata.flatten()) # add new recording to buffer
    
    print(f'size: {len(buffer)} buf1: {buffer}')
    
    threading.Thread(target=process_recording,args=(buffer,)).start() # leave processing to thread

def process_recording(buffer):
    # do some processing on the buffer
    #print(f'proc2: {buffer}')
    timestamp = time.strftime('%H_%M_%S', time.localtime())
    filename = f"recording_{timestamp}.csv"
    
    fs = 1000
    nfft = 8192
    frame_size = 1
    overlap = 0
    ENF = estimate_ENF(buffer, fs, nfft, frame_size, overlap)

    real_data_lim = 6
    write_data(filename,ENF)
    # Save the recording to a wave file
    # sf.write(filename, data=buffer, samplerate=44100)

# set up the recording parameters
buffer_duration = 7 # in seconds
fs = 1000
frame_cnt = int(fs * buffer_duration)
device_name = 'Microphone (3- USB Audio Device'

# start the recording
with sd.InputStream(device=device_name, callback=callback, channels=1,blocksize=frame_cnt, samplerate=fs):
    while True:
        pass
