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

f = open('./package/settings.json', 'r')
settings = json.loads(f.read())

harpia.set_spectra_per_acquisition(settings['spectra_per_acquisition'])

mb = MotorBoard(settings['can_id'], HarpiaCanSender(harpia))

diag_unit = PolarizationDiagnosticsUnit(mb, settings['motor_index'], settings['reduction'], settings.get("speed") or 10000, r'package/Sanyo Denki SH2281-5631 (rotary).json', settings.get("zero_angle") or 0.0)


def get_intensity():
    return np.abs(np.average(harpia._get('Basic/RawSignal')[settings['signal']]))

def get_polarization_information():
    angles = np.array([])
    intensities = np.array([])    
        
    # MEASURE    
    diag_unit.stop()
    
    init_angle = diag_unit.get_angle() % 360.0
    current_angle = init_angle
    
    diag_unit.start()   

    cnt = 0.0
    while cnt < 360.0:
        old_angle = current_angle
        current_angle = diag_unit.get_angle()
        if current_angle < old_angle:
            cnt = cnt + current_angle + 360.0 - old_angle
        else:
            cnt = cnt + current_angle - old_angle
        angles = np.append(angles, [current_angle])
        intensities = np.append(intensities, [get_intensity()])
        
    diag_unit.stop()
    
    # ANALYZE
    t1_ind = np.argmax(intensities)
    T1 = np.max(intensities)
    t2_ind = np.argmin(intensities)
    T2 = intensities[t2_ind]
    
    polarization_angle = angles[t2_ind]    
    polarization_angle = polarization_angle if polarization_angle < 180.0 else polarization_angle - 180.0
    
    P = (T1 - T2) / (T1 + T2)
    rho_P = T2/T1
    
    return {"rho_p": rho_P, "extinction": 1.0/rho_P, "efficiency": P, "polarization_angle": polarization_angle}

def go_to(par):
    if par[0] is not None:    
        harpia.set_berek_rotator_target_rotate_angle(par[0])
    if par[1] is not None:                
        harpia.set_berek_rotator_target_tilt_angle(par[1])

def fun_linear(par):
    go_to(par)

    score = get_intensity()

    print(par, score)

    return score

def fun_circular(par):
    go_to(par)
        
    data = get_polarization_information()
    
    score = data['extinction']

    print(par, score)
        
    return score

def fun_rotate(par):
    return fun([par[0], None])


def line_search_tilt(start, step):
    par = [None, start]
    score = fun(par)
    min_score = score
    cont = True
    i = 0
    
    while cont:
        i = i + 1
        par = [None, par[1] + step]
        score = fun(par)               
        cont = (score < min_score) and i < 20
        
        if score < min_score:
            min_score = score
        
    go_to([None, par[1] - step])        

def hooke_jeeves(fun, par, delta = 1.0, alpha = 0.5, step_min = 0.3):
    cont = True
    n_dim = len(par)
    
    move_vector = np.zeros(n_dim)
    x_new = fun(par)
    x = x_new
    step = delta
    i_iter = 0
    
    while (cont):            
        i_iter = i_iter + 1
        # evaluate vector
        for i in np.arange(n_dim):                
            x1 = fun(par + step * np.identity(2)[i])
            x2 = fun(par - step * np.identity(2)[i])
            
            if (x1 < x2) and (x1 < x):
                move_vector[i] = step
                x = x1
            elif (x2 < x1) and (x2 < x):
                move_vector[i] = -step
                x = x2
            elif (x <= x1) and (x <= x2):
                move_vector[i] = 0.0
                x = x
                
        print(x, x1, x2, move_vector)
        
        # reduce step
        if np.all(np.array(move_vector) == np.zeros(n_dim)):
            step = step * alpha
            print ("reduce", step)
        else:
            cont_move = True
            par = par + move_vector
            i_moves = 0
            while cont_move: 
                i_moves = i_moves + 1
                par = par + move_vector
                x_new = fun(par)
                cont_move = x_new < x
                if cont_move:
                    x = x_new            
            par = par - move_vector
            print ("stop", par)
            
        cont = i_iter < 10 and step >= step_min

class Worker(QObject):
    finished = pyqtSignal()
    progress = pyqtSignal(dict)
    target_lp_angle = 0

    ## FOR LINEAR
    def set_lp(self):
        self.is_running = True

        diag_unit.set_angle(self.target_lp_angle)
        diag_unit.wait_until_stopped()
        hooke_jeeves(fun_linear, [harpia.berek_rotator_actual_rotate_angle(), harpia.berek_rotator_actual_tilt_angle()], delta = 7.0, step_min = 0.125)

        self.progress.emit({'rotate': harpia.berek_rotator_actual_rotate_angle(), 'tilt': harpia.berek_rotator_actual_tilt_angle(), 'data': get_polarization_information()})
        self.finished.emit()
        
    ## FOR CIRCULAR
    def set_cp(self):
        self.is_running = True

        hooke_jeeves(fun_circular, [harpia.berek_rotator_actual_rotate_angle(), harpia.berek_rotator_actual_tilt_angle()], delta = 7.0, step_min = 0.125)

        self.progress.emit({'rotate': harpia.berek_rotator_actual_rotate_angle(), 'tilt': harpia.berek_rotator_actual_tilt_angle(), 'data': get_polarization_information()})
        self.finished.emit()
    

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
        #self.setGeometry(self.left, self.top, self.width, self.height)
        
        statusRowLayout = QHBoxLayout()
        self.status_message_label = QLabel('idle')
        statusRowLayout.addWidget(QLabel('STATUS: '))
        statusRowLayout.addWidget(self.status_message_label)
        statusRowLayout.addStretch()

        linearPolarizationLayout = QHBoxLayout()
        self.target_lp_textbox = QLineEdit()
        self.target_lp_textbox.setText('0.0')
        self.set_lp_btn = QPushButton('Set linear polarization')
        self.set_lp_btn.clicked.connect(self.set_lp)
        linearPolarizationLayout.addWidget(QLabel('Target angle, deg:'))
        linearPolarizationLayout.addWidget(self.target_lp_textbox)
        linearPolarizationLayout.addWidget(self.set_lp_btn)

        circularPolarizationLayout = QHBoxLayout()
        self.set_cp_btn = QPushButton('Set circular polarization')
        self.set_cp_btn.clicked.connect(self.set_cp)
        circularPolarizationLayout.addWidget(self.set_cp_btn)

        outerLayout = QVBoxLayout()

        outerLayout.addLayout(statusRowLayout)
        outerLayout.addLayout(linearPolarizationLayout)
        outerLayout.addLayout(circularPolarizationLayout)
        
        widget = QWidget()
        widget.setLayout(outerLayout)

        self.setCentralWidget(widget)  
        self.show()
        
    def set_lp_task(self, target):        
        self.thread = QThread()
        self.worker = Worker()
        self.worker.moveToThread(self.thread)
        self.worker.target_lp_angle = target
        self.thread.started.connect(self.worker.set_lp)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.progress.connect(self.print_lp_status)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.enableButtons)
        self.thread.start()
        # Final resets       
        # self.thread.finished.connect(self.addToPlots)

    def set_cp_task(self):        
        self.thread = QThread()
        self.worker = Worker()
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.set_cp)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.progress.connect(self.print_cp_status)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.enableButtons)
        self.thread.start()

    def updatePlots(self, info): 
        if (not self.canDraw) and (not info['finalize']): return()
        self.canDraw = False
        intensities = info['intensities']
        angles = info['angles']
        if info['finalize'] :
            self.sc[0].line.set_xdata(np.concatenate(((angles[angles<np.pi*2])[:-1], [angles[0] + np.pi * 2])))
            self.sc[0].line.set_ydata(np.concatenate(((intensities[angles<np.pi*2])[:-1], [intensities[0]])))
        else:            
            self.sc[0].line.set_xdata((angles[angles<np.pi*2])[:-1])
            self.sc[0].line.set_ydata((intensities[angles<np.pi*2])[:-1])
        
            pars = analyze(intensities)        
            if pars:
                tangle = angles[pars["min_ind"]]
                self.sc[0].maxpolline.set_xdata(np.array([tangle, np.pi+tangle]))
                self.sc[0].maxpolline.set_ydata([np.max(intensities)]*2)
                self.sc[0].minpolline.set_xdata([tangle + np.pi/2.0, np.pi + np.pi/2.0 +tangle])
                self.sc[0].minpolline.set_ydata([np.max(intensities)]*2)
            
                self.sc[0].ax.set_title("{:.2f}:1, efficiency {:.2f}".format(pars["extinction"], pars["efficiency"]))
        
                self.sc[0].ax.set_ylim([0, np.max(intensities)])
        
        self.sc[0].draw()
        app.processEvents()
        self.canDraw = True
                
    def print_lp_status(self, info):
        status = info['data']
        self.status_message_label.setText("linear polarization was set to {:.2f} deg, {:.2f}:1, efficiency {:.2f}".format(status["polarization_angle"], status["extinction"], status["efficiency"]))

    def print_cp_status(self, info):
        status = info['data']
        self.status_message_label.setText("circular polarization was set, {:.2f}:1".format(status["extinction"]))

    def enableButtons(self):
        self.set_lp_btn.setEnabled(True)
        self.set_cp_btn.setEnabled(True)

    def disableButtons(self):
        self.set_lp_btn.setEnabled(False)
        self.set_cp_btn.setEnabled(False)
        
    @pyqtSlot()
    def set_lp(self):
        target = float(self.target_lp_textbox.text())
        self.status_message_label.setText(f'setting linear polarization to {target:.2f} deg...')
        self.set_lp_task(target)
        self.disableButtons()

    @pyqtSlot()
    def set_cp(self):
        self.status_message_label.setText('setting circular polarization...')
        self.set_cp_task()
        self.disableButtons()
            

app = QApplication([])
w = MainWindow('HARPIA Polarization control')
app.exec_()