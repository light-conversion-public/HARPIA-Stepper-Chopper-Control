#!/usr/bin/env python
# -*- coding: utf-8 -*-
#==========================================================================
# 
#--------------------------------------------------------------------------
# Copyright (c) 2022 Light Conversion, UAB
# All rights reserved.
# www.lightcon.com
#==========================================================================
import numpy as np
import matplotlib.pyplot as plt
import lightcon.style

import json
import time

from LepreCan import LepreCanDevice, FrameType, BytesArrayToInt

from lightcon.harpia import Harpia

class MotorBoard:
    baseId = 0x000
    sender = None
    lcan = None
    
    reg_dict = { 'HardHiZ' : ('HIZ {:} HARD', 0x00A8),
                'AbsPos' : ('',0x0001),
                'CurrentSpeed': ('', 0x0004),
                'Stop' : ('',0x00B8),
                'GoTo' : ('', 0x0060),
                'RunForward' : ('RUN {:} 0', 0x0051),
                'RunReverse' : ('RUN {:} 1', 0x0050),
                'Acc' : ('ACC', 0x0005), 
                 'Dec' : ('DEC', 0x0006),
                 'FnSlpAcc' : ('FN_SLP_ACC', 0x000F),
                 'FnSlpDec' : ('FN_SLP_DEC', 0x0010),
                 'IntSpeed' : ('INT_SPEED', 0x000D),
                 'KTherm' : ('K_THERM', 0x0011), 
                 'KvalAcc' : ('KVAL_ACC', 0x000B),
                 'KvalDec' : ('KVAL_DEC', 0x000C),
                 'KvalHold' : ('KVAL_HOLD', 0x0009),
                 'KvalRun' : ('KVAL_RUN', 0x000A),
                 'MaxSpeed' : ('MAX_SPEED', 0x0007),
                 'MinSpeed' : ('MIN_SPEED', 0x0008),
                 'OcdTh' : ('OCD_TH', 0x0013),
                 'StSlp' : ('ST_SLP', 0x000E),
                 'StallTh' : ('STALL_TH', 0x0014),
                 'StepMode' : ('STEP_MODE', 0x0016),
                 'Status' : ('STATUS', 0x0019),
                 'LSStatus': ('', 0x0100),
                 'LSEnable': ('', 0x0103)}
    
    def __init__(self, _baseId, _sender, _speed = 10000):
        self.baseId = _baseId
        self.lcan = LepreCanDevice(None, 456)
        self.sender = _sender
        self.speed = _speed
        
    def is_stopped(self, motor_index):
        status = parse_int_from_response(self.get_register(self.reg_dict['Status'][1], motor_index))
            
        stopped = ((status >> 5) & 0x03) == 0 

        return stopped

    def wait_until_stopped(self, motor_index):
        """Wait until motor stops."""
        stopped = False        

        while not stopped:
            stopped = self.is_stopped(motor_index)                
            
            print ('position', parse_int_from_response(self.get_register(self.reg_dict['AbsPos'][1], motor_index)))

            time.sleep(0.05)
    def set_register(self, registerAddress, index = 0, value = 0):
        if type(value) == float:
            data4bytes = self.lcan.float_to_hex(value)
        if type(value) == int:
            data4bytes = value
        frame = self.lcan.GenerateDataFrame(FrameType.SetRegisterCommandFrame, registerAddress, index, 0x00, data4bytes)
        
        message = ''.join(['{0:0{1}x}'.format(b,2) for b in frame])
        
        response = self.sender.set_register(self.baseId, message)
        return response
    def get_register(self, registerAddress, index = 0):
        frame = self.lcan.GenerateDataFrame(FrameType.SetRegisterCommandFrame, registerAddress, index, 0x00, 0)
        response = self.sender.get_register(self.baseId, ''.join(['{0:0{1}x}'.format(b,2) for b in frame]))
        
        return response
        
    def setup_motor(self, index, file_name):                
        try:
            with open(file_name, 'r') as f:
                motor_info = json.loads(f.read())            
                
        except FileNotFoundError:
            print ('Configuration not found')
            return        
    
        response = self.set_register(self.reg_dict['HardHiZ'][1], 1)
        time.sleep(1)    
        
        for key in motor_info.keys():
            if self.reg_dict.get(key):
                
                response = self.set_register(self.reg_dict[key][1], index, motor_info[key])
                print ('<', response, 'for', key)
    
    def reset_motor(self, index):
        self.set_register(self.reg_dict['RunForward'][1], self.speed)
        
class HarpiaCanSender:
    harpia = None
    def __init__ (self, _harpia):
        self.harpia = _harpia
        
    def set_register(self, baseId, data8bytes):
        return self.harpia._get('Advanced/SetCanRegister/{:}/{:}'.format(baseId, data8bytes))
        
    def get_register(self, baseId, data8bytes):
        return self.harpia._get('Advanced/GetCanRegister/{:}/{:}'.format(baseId, data8bytes))
        
def parse_int_from_response(response):
    data4bytes = [int('0x'+response[i:i+2], 16) for i in np.arange(0, len(response),2)][-4:]
    return BytesArrayToInt(data4bytes)

class StepperChopper:
    full_steps_per_revolution = 400
    seconds_per_tick28 = 67.108864

    def __init__ (self, mb, motor_index, blades, motor_config):
        self.mb = mb
        self.motor_index = motor_index
        self.motor_config = motor_config        
        self.blades = blades

        self.init_and_reset_if_stopped()

    def calculate_speed(self, freq):
        steps_per_second = self.full_steps_per_revolution / self.blades * freq
        steps_per_tick = steps_per_second * self.seconds_per_tick28
        return int(steps_per_tick)
    
    def get_freq(self):
        steps_per_tick = parse_int_from_response(self.mb.get_register(self.mb.reg_dict['CurrentSpeed'][1], self.motor_index))
        steps_per_second = steps_per_tick / self.seconds_per_tick28
        return steps_per_second / self.full_steps_per_revolution * self.blades

    def is_running(self):
        return not self.mb.is_stopped(self.motor_index)

    def stop(self):
        self.mb.set_register(self.mb.reg_dict['Stop'][1], self.motor_index, 0)
        
    def start(self, freq):
        target_speed = self.calculate_speed(freq)
        self.mb.set_register(self.mb.reg_dict['RunForward'][1], self.motor_index, target_speed)
    
    def init_and_reset_if_stopped(self):
        if self.mb.is_stopped(self.motor_index):
            self.mb.set_register(self.mb.reg_dict['HardHiZ'][1], self.motor_index, 1)
            self.mb.setup_motor(self.motor_index, self.motor_config)        

        self.step_mode = parse_int_from_response(self.mb.get_register(self.mb.reg_dict['StepMode'][1], self.motor_index))
        self.mb.set_register(self.mb.reg_dict['LSEnable'][1], self.motor_index, 0)