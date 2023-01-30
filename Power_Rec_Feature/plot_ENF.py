import csv
import matplotlib.pyplot as plt
import numpy as np
import time
import os
import math
from scipy.stats.stats import pearsonr

# Constants for file location

folder1 = 'ENF_Data1/'
folder2 = 'ENF_Data2/'
folder3 = 'ENF_Data3/'

#function to compare the signal similarities

def correlation_vector(ENF_signal1, ENF_signal2, window_size, shift_size):
    correlation_ENF = []
    length_of_signal = min(len(ENF_signal1), len(ENF_signal2))
    total_windows = math.ceil(( length_of_signal - window_size + 1) / shift_size)
    rho = np.zeros((1,total_windows))
    for i in range(0,total_windows):
        enf_sig1 = ENF_signal1[i * shift_size: i * shift_size + window_size]
        enf_sig2 = ENF_signal2[i * shift_size: i * shift_size + window_size]
        enf_sig1 = np.reshape(enf_sig1, (len(enf_sig1),))
        enf_sig2 = np.reshape(enf_sig2,(len(enf_sig2), ))
        r,p = pearsonr(enf_sig1, enf_sig2)
        rho[0][i] = r
    return rho,total_windows

def read_enf_signal(filepath):
    with open(filepath, 'r') as csv_file:
        ENF = []
        csv_reader = csv.reader(csv_file)

        next(csv_reader) #skip 1st line

        for item in csv_reader:
            ENF = np.append(ENF, float(item[1]))
    
    return ENF

def main():
    data_size = 1800
    ENF1 = []
    list_files = os.listdir(folder1)

    for filename in list_files: # compute ENF in every file
        filepath = folder1 + filename

        read_ENF = read_enf_signal(filepath)
        ENF1 = np.append(ENF1, read_ENF)

    ENF2 = []
    list_files = os.listdir(folder2)

    for filename in list_files: # compute ENF in every file
        filepath = folder2 + filename

        read_ENF = read_enf_signal(filepath)
        ENF2 = np.append(ENF2, read_ENF)

    ENF3 = []
    list_files = os.listdir(folder3)

    for filename in list_files: # compute ENF in every file
        filepath = folder3 + filename

        read_ENF = read_enf_signal(filepath)
        ENF3 = np.append(ENF3, read_ENF)
    
    data1 = ENF1
    data2 = ENF3

    plt.figure(1)
    plt.plot(ENF3,'m', label="Device 3")
    plt.plot(data1,'g', label="Device 1")
    plt.plot(data2,'c', label="Device 2")
    
    #plt.vlines(x= [data_size, data_size*2, data_size*3, data_size*4, data_size*5], ymin = 59.95, ymax = 60.05, colors= 'r', alpha = 0.5)
    plt.ylabel('Frequency (Hz)', fontsize=14)
    plt.xlabel('Time (sec)', fontsize=14)
    plt.title('24 Hour ENF Fluctuations', fontsize=14)
    plt.legend(loc="lower right")
    plt.show()
    
    window_size = 60
    shift_size = 5
    rho,total_windows = correlation_vector(data1, data2,window_size,shift_size)
    
    # Display the correlation

    plt.figure(2)
    t = np.arange(0,total_windows-1,1)
    plt.plot(t,rho[0][1:],'g--', label="Plain Wall")
    plt.hlines(y=0.8, xmin=0, xmax=len(t), colors='r', linestyles='--', lw=2)
    plt.ylabel('Correlation Coefficient', fontsize=12)
    plt.xlabel('Number of Windows compared', fontsize=12)
    plt.title('ENF fluctuations compared', fontsize=12)
    plt.legend(loc="lower right")
    plt.show()
    
if __name__ == '__main__':
    main()

