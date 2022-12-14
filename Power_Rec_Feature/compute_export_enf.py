from googleapiclient.http import MediaFileUpload
from Google import Create_Service
from datetime import datetime
import pyenf
import librosa
import csv
import numpy as np
import time
import os
import pandas as pd
import shutil

# Constants for file locations
folder_archive = 'Archived_Recordings/'
folder_audio = 'Power_Recordings/'
folder_enf = 'ENF_Data/'

## Create google drive service instance
CLIENT_SECRET_FILE = 'credentials.json'
API_NAME = 'drive'
API_VERSION = 'v3'
SCOPES = ['https://www.googleapis.com/auth/drive']
folder_database_id = '1iAwz3R8AY3rn6r6lruN_tYfh_7cYjjD5' #upload to database folder
dev = 'Dev1'

def compute_ENF(filepath, duration):
    #parameters for the STFT algorithm

    fs = 1000  # downsampling frequency
    nfft = 8192
    frame_size = 2  # change it to 6 for videos with large length recording
    overlap = 0

    ## Reading from csv file - takes tooo long
    #enf_signal = read_enf_signal(filepath)

    ## Loading audio file
    enf_signal_filename = filepath
    enf_signal, fs = librosa.load(enf_signal_filename, sr=fs)  # loading the power ENF data

    enf_signal_object = pyenf.pyENF(signal0=enf_signal, fs=fs, nominal=60, harmonic_multiples=1, duration=0.1,
                                    strip_index=0, frame_size_secs=frame_size, nfft=nfft, overlap_amount_secs=overlap)
    enf_spectro_strip, enf_frequency_support = enf_signal_object.compute_spectrogam_strips()
    enf_weights = enf_signal_object.compute_combining_weights_from_harmonics()
    enf_OurStripCell, enf_initial_frequency = enf_signal_object.compute_combined_spectrum(enf_spectro_strip,
                                                                                          enf_weights,
                                                                                          enf_frequency_support)
    estimated_ENF = enf_signal_object.compute_ENF_from_combined_strip(enf_OurStripCell, enf_initial_frequency)
    estimated_ENF = np.array(estimated_ENF).T.flatten()
    estimated_ENF = estimated_ENF[:(duration//frame_size)] # exclude extra ENF point
    return estimated_ENF

def write_data(csv_filename, data): # write data to csv file
    cnt = 0
    timestamp = parse_filename(csv_filename)
    UTC_timestamp = f"UTC: {timestamp[0]}-{timestamp[1]}-{timestamp[2]} {timestamp[3]}:{timestamp[4]}:{timestamp[5]}"
    
    with open(folder_enf + dev + '_ENF_Hr' + str(timestamp[3]) + '.csv', 'w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file)

        csv_writer.writerow([UTC_timestamp, ' Duration: 1 Hour'])
        for item in data: # Counter, ENF value
            csv_writer.writerow([str(cnt), str(item)])
            cnt += 1

def read_file(filepath): # return date read from csv file
    with open(filepath, 'r') as csv_file:
        csv_reader = csv.reader(csv_file)

        UTC_date = (list(csv_reader))[0][0]
        
    return f'{UTC_date[5:9]}_{UTC_date[10:12]}_{UTC_date[13:15]}'

def parse_filename(filename): # %Y_m_d_H_M_S
    
    timestamp = []
    for i in range(6):
        timestamp.append(filename[0:filename.find('_')])
        filename = filename[filename.find('_')+1:]
     
    return timestamp

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
    media = MediaFileUpload(folder_enf+'{0}'.format(file_name), mimetype=mime_types)

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
        new_folder_id = create_folder(service, folder_database_id, dev + 'Power_ENF_'+target)
        upload_file(service,new_folder_id, file_name)

def remove_file(filepath):
    try:
        os.remove(filepath) #remove file
    except FileNotFoundError:
        print('File not found')
    except PermissionError:
        print('You do not have permission to delete')

def cleanup():
    list_archived_files = os.listdir(folder_archive)
    if (not list_archived_files):
        return #exit function
    for filename in list_archived_files:
        filepath = folder_archive + filename
        c_time = os.path.getctime(filepath) # File creation timestamp

        dt_c = datetime.now() # Current local timestamp
        delta_time = dt_c - datetime.fromtimestamp(c_time)

        if (delta_time.days > 14): # Remove files older than 2 weeks
            remove_file(filepath)

def main():
    dur_minute = 60
    duration = (60*dur_minute) 
    # Create Google Drive service instance
    service = Create_Service(CLIENT_SECRET_FILE, API_NAME, API_VERSION, SCOPES)

    while(True):
        cleanup() # Archived Recording maintenance

        # loop back to check for more files to estimate
        list_audio_files = os.listdir(folder_audio)

        if (not list_audio_files): 
            print('Folder empty')
            time.sleep(3600) # sleep for some time
            continue
        
        for filename in list_audio_files: # compute ENF in every file
            filepath = folder_audio + filename
            ENF = compute_ENF(filepath, duration)
            write_data(filename[:-3], ENF) ## write ENF to csv
        
        # export to Google Drive (check year,month,day)
        list_ENF_files = os.listdir(folder_enf)
        
        for filename in list_ENF_files:
            filepath = folder_enf + filename
            target = read_file(filepath)# Check date from csv file
            scan_folders(service,target,filename) # scan and upload files to proper folder
        
        for filename in list_audio_files: # Archive audio recordings
            filepath = folder_audio + filename
            shutil.move(filepath, folder_archive)

        for filename in list_ENF_files: # All estimation complete and exported, clean up files in ENF_Data
            filepath = folder_enf + filename
            remove_file(filepath) 

if __name__ == '__main__':
    main()
