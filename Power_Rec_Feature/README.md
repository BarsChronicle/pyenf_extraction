# power_rec_even_hr
Python based, power recordings for an hour. This code only records even hours and should be used in parallel with the power_rec_odd_hr
to caputure every hour.

# compute_export_enf
Periodically reads from the Power_Recordings folder to compute ENF and the output csv is saved to ENF_Data. At the end, the ENF will
be timestamped and exported to selected Google Drive folder. Make adjustment to the filepath if need be.

# Google and demo
Open-source code used to create the Google Drive service instance. Must include json credentials to your Google Drive API to properly use
this code. Use the provided demo code to authenticate access to your Google drive (only need to be done once)

# Testing functionality
Make sure to run demo.py so that the program has access to the Google drive. Run power_rec_even_hr.py and power_rec_odd_hr.py to record
every hour. Also run compute_export_enf.py to compute and export enf to the database. These three programs should be ran be in parallel.
