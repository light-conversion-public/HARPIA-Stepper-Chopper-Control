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

with open('./package/known_datapoints.json', 'r') as fk:
    known_datapoints = json.loads(fk.read())


harpia.set_spectra_per_acquisition(settings['spectra_per_acquisition'])

mb = MotorBoard(settings['can_id'], HarpiaCanSender(harpia))

diag_unit = PolarizationDiagnosticsUnit(mb, settings['motor_index'], settings['reduction'], settings.get("speed") or 10000, r'package/Sanyo Denki SH2281-5631 (rotary).json')


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

def fun(par):
    go_to(par)
        
    data = get_polarization_information()
    
    score = 0.0
    if target == "lcp" or target == "rcp":
        score = data['extinction']
    else:
        score = np.min([np.abs(data['polarization_angle'] - target), np.abs(data['polarization_angle'] - 180.0 - target)]) + data['rho_p'] * 200.0
    
    print(par, score, data)
        
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

# FOR CIRCULAR
#line_search_tilt(harpia.berek_rotator_actual_tilt_angle() - 15.0, 2.0)
#hooke_jeeves(fun_rotate, [harpia.berek_rotator_actual_rotate_angle()], delta = 4.0, step_min = 1.0)

#line_search_tilt(harpia.berek_rotator_actual_tilt_angle() - 2.0, 0.5)
#hooke_jeeves(fun_rotate, [harpia.berek_rotator_actual_rotate_angle()], delta = 1.0, step_min = 0.25)

#known_datapoints[target] = {'rotate': harpia.berek_rotator_actual_rotate_angle(), 'tilt': harpia.berek_rotator_actual_rotate_angle()}


for target in np.arange(0.0, 90.0, 5.0):
    # FOR LINEAR
    hooke_jeeves(fun, [harpia.berek_rotator_actual_rotate_angle(), harpia.berek_rotator_actual_tilt_angle()], delta = 5.0, step_min = 0.125)
    known_datapoints[target] = {'rotate': harpia.berek_rotator_actual_rotate_angle(), 'tilt': harpia.berek_rotator_actual_tilt_angle(), 'data': get_polarization_information()}


    with open("./package/known_datapoints.json", "w") as f:
        json.dump(known_datapoints, f, indent = 2)