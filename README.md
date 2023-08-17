# HARPIA Stepper chopper control package
This script is a software for controlling the HARPIA stepper chopper for low-frequency 
pump signal chopping. Stepper chopper is an optional extension of HARPIA Spectroscopy System.

## Requirements
 - Installed Light Conversion Launcher application. It is used to run this 
   script.
 - Installed and running HARPIA Service App. Connection with the spectrograph 
   must be successful.
 - HARPIA Spectroscopy Systems with the stepper chopper installed 
 
## Configuration
 - Start the Launcher application
 - In 'Packages' tab, choose 'Add New Package' and select 'main.py' file 
   of this package
 - The 'HARPIA REST' should be indicated as connected at '127.0.0.1' under the
   'Required connections'. If not, check HARPIA Service App and choose 'Refresh'
   in 'Connections' tab
 
## Operation 
 - Run the HARPIA Stepper Chopper Control script using the Launcher application
   by clicking 'Start'
 - Use buttons 'RUN' and 'STOP' to start running at the target frequency or stop.
 
## Advanced
Advanced settings can be changed in the 'settings.json' file
 - 'can_id': (default 480) CAN bus id (448 for primary, 456 - secondary, 480 - tertiary,
   464 - TB, 472- TF motor boards)
 - 'motor_index': (default 0) Motor index of the corresponding motor  board 
 - 'blades': (default 10) Number of blades per chopper
 - 'frequency': Last used frequency