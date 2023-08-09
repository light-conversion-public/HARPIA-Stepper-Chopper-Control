#!/usr/bin/env python
# -*- coding: utf-8 -*-
#==========================================================================
# Harpia REST API Interface example
#--------------------------------------------------------------------------
# Copyright (c) 2019 Light Conversion
# All rights reserved.
# www.lightcon.com
#==========================================================================
# In this example, uprocessed raw data is read from Harpia with chopper opened
# and the pump photiode data is processed to evaluate stability. 
 

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

harpia = Harpia('127.0.0.1')
harpia.set_spectra_per_acquisition(settings['spectra_per_acquisition'])

mb = MotorBoard(settings['can_id'], HarpiaCanSender(harpia))

diag_unit = PolarizationDiagnosticsUnit(mb, settings['motor_index'], settings['reduction'], settings.get("speed") or 10000, r'package/Sanyo Denki SH2281-5631 (rotary).json')

score_type = "cp"

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
        angles = np.append(angles, [(current_angle) / 180.0 * np.pi])
        intensities = np.append(intensities, [get_intensity()])
        
    diag_unit.stop()
    
    # ANALYZE
    t1_ind = np.argmax(intensities)
    T1 = np.max(intensities)
    t2_ind = np.argmin(intensities)
    T2 = intensities[t2_ind]
    
    polarization_angle = ((angles[t1_ind] + 90.0 + 360.0) % 360.0) % 180.0
    
    P = (T1 - T2) / (T1 + T2)
    rho_P = T2/T1
    
    return {"rho_p": rho_P, "extinction": 1.0/rho_P, "efficiency": P, "min_ind": t2_ind, "polarization_angle": polarization_angle}

def go_to(par):
    if par[0] is not None:        
        harpia.set_berek_rotator_target_rotate_angle(par[0])
    if par[1] is not None:        
        harpia.set_berek_rotator_target_tilt_angle(par[1])

def fun(par):
    go_to(par)
        
    data = get_polarization_information()
    
    print(par, data)
    
    score = 0.0
    if score_type == "cp":
        score = data['efficiency']
        
    return score

def fun_rotate(par):
    return fun([par[0], None])


def line_search(start, step):
    par = [None, start]
    score = fun(par)
    min_score = score
    cont = True
    
    while cont:
        par = [None, par[0] + step]
        score = fun(par)
        
        cont = score < min_score
        
    go_to([None, par[0] - step])        



# harpia._put("/BerekRotator/TargetLinearPolarization", str(target_polarization_angle))

harpia._put("/BerekRotator/TargetCircularPolarization", "R")
par = [harpia.berek_rotator_actual_rotate_angle(), harpia.berek_rotator_actual_tilt_angle()]

line_search(harpia.berek_rotator_actual_tilt_angle() - 5.0, 1.0)



#%% STOCHASTIC OPTIMIZATION
def stochastic_optimization(fun, x_init, lower=None, upper=None, a_min = 0.005, a_init = 0.1, c_init = 3.0, alpha = 1.0, gamma = 0.3, A = 1.0, **kwargs):
    scaling_coeffs = kwargs.get('scaling_coeffs', None)
    
    n = len(x_init)
    
    #test, whether lengths are correct    
    if scaling_coeffs:
        if len(scaling_coeffs) != n:
            print('Length of scaling_coeffs does not match parameter count')
            return
    else:
        scaling_coeffs = np.ones(n)
    
    x = x_init
    a = a_init
    c = c_init
    iteration = 0
    

    avals = [a_init]    
    xvals = [x]
    fvals = [fun(x)]
    
    np.random.seed(int((time.time() % 1.0)*1000))
    
    while a > a_min:
        d = (np.random.randint(0,2,size=n) - 0.5 ) * 2
        d = np.diag([1]*n)[np.random.randint(0,n)]*(np.random.randint(0,2,size=n) - 0.5 ) * 2
                                
        par1 = np.array([ix + scaling_coeffs[it] * c * d[it] for it, ix in enumerate(x)])            
        par2 = np.array([ix - scaling_coeffs[it] * c * d[it] for it, ix in enumerate(x)])
        
        if lower is not None:
            for it,_ in enumerate(x):
                if par1[it]<lower[it]:
                    par1[it] = ix - scaling_coeffs[it] * c * d[it]
                if par2[it]<lower[it]:
                    par2[it] = ix + scaling_coeffs[it] * c * d[it]
        if upper is not None:
            for it,_ in enumerate(x):
                if par1[it]>upper[it]:
                    par1[it] = upper[it]
                if par2[it]>upper[it]:
                    par2[it] = upper[it]
                
        f1 = fun(par1)
        f2 = fun(par2)            
    
        fvals.append((f1,f2));
        avals.append([a])
        
        x = x + np.array([scaling_coeffs[i] * a * (f1 - f2) / 2.0 / c / d[i] if d[i]!=0 else 0 for i, ix in enumerate(x)])        
                    
        iteration = iteration + 1
        
        a = a_init / (A + iteration) ** alpha
        c = c_init / iteration ** gamma
        
        xvals.append(list(x))
        avals.append([a])            
    
    return {'x': x, 'xvals': xvals, 'fvals': fvals}






