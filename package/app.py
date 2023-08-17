#!/usr/bin/env python
# -*- coding: utf-8 -*-
#==========================================================================
# HARPIA Polarization Diagnostics Tool
#--------------------------------------------------------------------------
# Copyright (c) 2022 Light Conversion, UAB
# All rights reserved.
# www.lightcon.com
#==========================================================================
     
import lclauncher

import os
import sys    
import time
import numpy as np
import lightcon.style
import json

# lightcon.style.apply_style()

sys.path.append(os.path.dirname(os.path.realpath(sys.argv[0])))
os.chdir(os.path.dirname(os.path.realpath(sys.argv[0])))

# if connections to devices are used, they are initiated here:
connections = lclauncher.establish_connections()

# initialize and connect to HARPIA
harpia = connections.get_connection('harpia')

# check if connection successful
if not harpia:
    sys.exit("Could not connect to Harpia")


from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import pyqtSlot, QObject, QThread, pyqtSignal
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib import pyplot, transforms
import numpy as np
import sys
import pickle
import time

from lightcon.harpia import Harpia
from utils import *

with open('./package/settings.json', 'r') as f:
    settings = json.loads(f.read())

mb = MotorBoard(settings['can_id'], HarpiaCanSender(harpia))

chopper = StepperChopper(mb, settings['motor_index'], settings.get('blades') or 10, r'package/Sanyo Denki 103-4902.json')

class Worker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(dict)

    def read_frequency(self):
        self.is_running = True

        while self.is_running:
            self.progress.emit({'frequency' : chopper.get_freq()})

class MainWindow(QMainWindow):
    sc = None
    canDraw = True    
    
    def __init__(self, title):
        super().__init__()
        self.title = title
        self.left = 100
        self.top = 100
        self.width = 900
        self.height = 900
        self.initUI()
        
            
    def initUI(self):
        self.setWindowTitle(self.title)
        
        statusRowLayout = QHBoxLayout()
        self.status_message_label = QLabel('idle')
        statusRowLayout.addWidget(QLabel('STATUS: '))
        statusRowLayout.addWidget(self.status_message_label)
        statusRowLayout.addStretch()

        controlRowLayout = QHBoxLayout()
        self.target_frequency_textbox = QLineEdit()
        self.target_frequency_textbox.setText("{:.1f}".format(settings.get('frequency') or 10.0))
        self.run_btn = QPushButton('RUN')
        self.run_btn.clicked.connect(self.run)
        self.stop_btn = QPushButton('STOP')
        self.stop_btn.clicked.connect(self.stop)
        controlRowLayout.addWidget(QLabel('Target frequency, Hz:'))
        controlRowLayout.addWidget(self.target_frequency_textbox)
        controlRowLayout.addWidget(self.run_btn)
        controlRowLayout.addWidget(self.stop_btn)

        outerLayout = QVBoxLayout()
        outerLayout.addLayout(statusRowLayout)
        outerLayout.addLayout(controlRowLayout)
        
        widget = QWidget()
        widget.setLayout(outerLayout)

        self.setCentralWidget(widget)  
        self.show()

        self.read_frequency_task()
        
    def read_frequency_task(self):        
        self.thread = QThread()
        self.worker = Worker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.read_frequency)
        self.worker.progress.connect(self.print_frequency_status)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()
        # Final resets       
        # self.thread.finished.connect(self.addToPlots)   
                
    def print_frequency_status(self, status):
        frequency = status['frequency']
        if frequency > 0.1:
            self.status_message_label.setText("running at {:.1f} Hz".format(frequency))
        else:
            self.status_message_label.setText("stopped")
        
    @pyqtSlot()
    def run(self):
        frequency = float(self.target_frequency_textbox.text())
        chopper.start(frequency)
        settings['frequency'] = frequency
        self.save_settings()

    @pyqtSlot()
    def stop(self):
        chopper.stop()

    def save_settings(self):
        with open('./package/settings.json', 'w') as f:
            json.dump(settings, f)


app = QApplication([])
w = MainWindow('HARPIA Stepper chopper control')
app.aboutToQuit.connect(w.save_settings)
app.exec_()