from googleapiclient.http import MediaFileUpload
from Google import Create_Service
import csv
import sounddevice as sd
import numpy as np
import time
import datetime
import threading
import pandas as pd
import pyenf
import ntplib
import sys
import os

# Set up the recording parameters
init_duration = 14
buffer_duration = 6 # in seconds

# ENF function parameters
fs = 1000
nfft = 8192
frame_size = 2
overlap = 0

## Create google drive service instance
CLIENT_SECRET_FILE = 'credentials.json'
API_NAME = 'drive'
API_VERSION = 'v3'
SCOPES = ['https://www.googleapis.com/auth/drive']
folder_database_id = '1bTsof1ewrz_BmH6gpq34PzJLMIkA5hBa' #upload to database folder
dev = 'Dev5'

service = Create_Service(CLIENT_SECRET_FILE, API_NAME, API_VERSION, SCOPES)

# Output & Time sync parameter
folderpath = 'ENF_Data' #change to absolute path of folder in computing hardware
UTC_timestamp = ''

# Recording buffers
ENF_vector = []
buffer = []

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

def write_data(data): # write data to csv file
    cnt = 0
    filename = dev + '_ENF_Hr' + UTC_timestamp.strftime('%H') + '.csv'
    with open(folderpath + filename, 'w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file)

        csv_writer.writerow([f"UTC: {UTC_timestamp}", ' Duration: 1 Hour'])
        for item in data: # Counter, ENF value
            csv_writer.writerow([str(cnt), str(item)])
            cnt += 1
    return filename

def create_folder(service, drive_id, folder_name):
    file_metadata = {
        'name' : folder_name,
        'mimeType' : 'application/vnd.google-apps.folder',
        'parents' : [drive_id] #create folder under another folder
    }

    file = service.files().create(
        body=file_metadata,
        fields='id',
        supportsAllDrives=True #allow access to share drive
    ).execute()

    folder_id = file.get('id')
    return folder_id

def upload_file(service, folder_id, file_name):
    mime_types = 'text/csv' # mimetype for each file type

    file_metadata = { #goes to body
        'name' : file_name,
        'parents' : [folder_id]
    }

    # specify folder name and provide mimetype; store output to object called media
    media = MediaFileUpload(folderpath+'{0}'.format(file_name), mimetype=mime_types)

    service.files().create(
        body = file_metadata,
        media_body = media,
        fields = 'id',
        supportsAllDrives=True #allow access to share drive
    ).execute()

def scan_folders(service, target, file_name):
    query = f"parents = '{folder_database_id}'" # folder (in URL) to upload

    while(True):
        try:
            response = service.files().list(q=query, includeItemsFromAllDrives=True, supportsAllDrives=True).execute()
        except Exception:
            pass
        else:
            files = response.get('files')
            break

    df = pd.DataFrame(files)
    df_id = df.get("id")
    df_name = df.get("name")

    create_folder_flag = 0
    #grab id and name
    try:
        for id, name in zip(df_id,df_name):
            # check if folder_name exists
            if target in str(name): # yes  ->> upload file
                upload_file(service,id, file_name)
                create_folder_flag = 1
                break
    except:
        pass
           
    if create_folder_flag == 0:    # no ->> create folder
        new_folder_id = create_folder(service, folder_database_id, dev + '_Power_ENF_'+target)
        upload_file(service,new_folder_id, file_name)

def remove_file(filepath):
    try:
        os.remove(filepath) #remove file
    except FileNotFoundError:
        print('File not found')
    except PermissionError:
        print('You do not have permission to delete')

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
    global buffer
    buffer = np.append(buffer,indata.flatten()) # add new recording to buffer

    if len(buffer) > ((init_duration+buffer_duration)*fs): # estimate from 20 secs recording
        buffer = buffer[(buffer_duration*fs):] # chop off first 6 secs from previous buffer
        flag = 1
    else: # 1st buffer
        flag = 0

    #print(f'size: {len(buffer)} buf1: {buffer}')
    threading.Thread(target=process_recording,args=(buffer,flag)).start() # leave processing to thread

def process_recording(buffer,flag):  
    global ENF_vector
    ENF = estimate_ENF(buffer)
    
    # Following configurations only for frame_size=2
    real_data_lim = -3 
    if flag == 1: # Susequent buffer chop repeating 1st 6 ENF data
        ENF = ENF[6:]

    # trim junk tailend
    ENF = ENF[:real_data_lim]
    ENF_vector = np.append(ENF_vector, ENF)
    
    if (len(ENF_vector) >= 1800):
        export_ENF = ENF_vector
        ENF_vector = ENF_vector[1800:] # push out ENF from the 1st hour
        threading.Thread(target=export_data,args=(export_ENF,)).start() # leave processing to thread
        
def export_data(data):
    global UTC_timestamp
    filename = write_data(data) # write ENF to csv
    filepath = folderpath + filename
    
    target = UTC_timestamp.strftime('%Y_%m_%d')
    scan_folders(service,target,filename) # export csv to database
    remove_file(filepath)

    UTC_timestamp = UTC_timestamp + datetime.timedelta(hours=1) # increment hour

def main():
    # Blocks the program until synchronized
    sync_wait()

    # Buffer 1st few seconds
    init_rec()

    frame_cnt = int(fs * buffer_duration)
    # buffer stream
    with sd.InputStream(callback=callback, channels=1,blocksize=frame_cnt, samplerate=fs):
        while True:
            pass

if __name__ == '__main__':
    main()
