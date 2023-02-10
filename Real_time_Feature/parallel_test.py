import csv
import matplotlib.pyplot as plt
import numpy as np
import time
import os
import math
from scipy.stats.stats import pearsonr

# Constants for file location

folder1 = 'RealtimeENF.csv'
folder2 = 'Continuous_hour.csv'

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
    ENF1 = read_enf_signal(folder1)
    ENF2 = read_ENF = read_enf_signal(folder2)

    plt.figure(1)
    plt.plot(ENF1,'g', label="Realtime ENF")
    plt.plot(ENF2,'c', label="Continuous hour session")
    
    #plt.vlines(x= [data_size, data_size*2, data_size*3, data_size*4, data_size*5], ymin = 59.95, ymax = 60.05, colors= 'r', alpha = 0.5)
    plt.ylabel('Frequency (Hz)', fontsize=14)
    plt.xlabel('Time (sec)', fontsize=14)
    plt.title('1 Hour ENF Fluctuations', fontsize=14)
    plt.legend(loc="lower right")
    plt.show()
    
    window_size = 60
    shift_size = 5
    rho,total_windows = correlation_vector(ENF1, ENF2,window_size,shift_size)
    
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

