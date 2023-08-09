# HARPIA Polarization control package
This script is a software for controlling the HARPIA Berek rotator and
Polarization Diagnostics Unit (PDU) in order to set the required polarization
(linear or circular). PDU is an optional extension of HARPIA Spectroscopy System.

## Requirements
 - Installed Light Conversion Launcher application. It is used to run this 
   script.
 - Installed and running HARPIA Service App. Connection with the spectrograph 
   must be successful.
 - PDU. It must be connected to system-specific HARPIA's motor control port
 - Photodiode, placed after the PDU for beam intensity acquisition
 
## Configuration
 - Start the Launcher application
 - In 'Packages' tab, choose 'Add New Package' and select 'main.py' file 
   of this package
 - The 'HARPIA REST' should be indicated as connected at '127.0.0.1' under the
   'Required connections'. If not, check HARPIA Service App and choose 'Refresh'
   in 'Connections' tab
 - OPTIONAL: Configure and run the HARPIA Polarization Diagnostics script using the Launcher 
   application. Ensure, that the polarization angle, measured by the script, is correct
 
## Operation
 - If polarization is ought to be measured for the pump beam, stop the HARPIA 
   chopper at position, not blocking the beam
 - Direct the beam to the photodiode by opening the corresponding shutter and
   adjusting beam routing optics if necessary
 - Run the HARPIA Polarization Diagnostics script using the Launcher application
   by clicking 'Start'
 - In HARPIA Service App, ensure, that the corresponding detector (default 
   "VIS array detector") is selected and its "AuxiliarySignal" value is set
   to the required analog channel.
 - Run the HARPIA Polarization Control script, insert the target linear polarization angle
   and click 'Set linear polarization' or click 'Set circular polarization'. Setting
   optimal parameters might take a few minutes.
 
## Advanced
Advanced settings can be changed in the 'settings.json' file
 - 'can_id': (default 448) CAN bus id (448 for primary, 456 - secondary, 
   464 - TB, 472- TF motor boards)
 - 'reduction'. Gear ratio of the PDU
 - 'motor_index': (default 2) Motor index of the corresponding motor  board
 - 'signal': Signal "AuxiliarySignal" (default), "PumpPhotodetectorSignal",
   'ProbePhotodetectorSignal' or "SpectrometerSignal" of the selected HARPIA 
   detector
 - 'speed': (default 30000) can be decreased for more accurate diagnostics 
   when setting circular polarization