# -*- coding: utf-8 -*-
"""
Created on Sat Jun  1 17:52:51 2024

@author: Christian Beckers chthbe@web.de
"""

import pandas as pd
import numpy as np
import datetime as dt

class volunteer:
    def __init__(self, name, experience, unavailable=[]):
        # unavailable is list of tuple [(date, from_time, to_time)]
        self.name=name
        self.experience=experience
        self.unavailable=unavailable
        self.assigned_shifts=[]
        self.infeasible_shifts=[]
        self.fav_location=[]
        
    def is_feasible(self, shift):
        # shift is tuple (location, date, from_time, to_time)
        if len(self.unavailable) == 0:
            return True
        else:
            res = True
            for unav in self.unavailable:
                if (unav[0] == shift[1]):
                    res = res & ((unav[1]>=shift[3]) | (unav[2]<=shift[2]))
            return res
                
    def is_unassigned(self, shift):
        # shift is tuple (location, date, from_time, to_time)
        if len(self.assigned_shifts) == 0:
            return True
        else:
            res = True
            for unav in self.assigned_shifts:
                if (unav[1] == shift[1]):
                    res = res & ((unav[2]>=shift[3]) | (unav[3]<=shift[2]))
            return res
        
    def assign_shift(self, shift):
        if self.is_feasible(shift) and self.is_unassigned(shift):
            self.assigned_shifts.append(shift)
            res = True
            print(f'Successfully assigned {shift}')
        else:
            self.infeasible_shifts.append(shift)
            res = False
            print(f'Infeasibly assigned {shift}')
        return res
    
    def update_shift_feasibility(self):
        for shift in self.infeasible_shifts:
            if self.is_feasible(shift) and self.is_unassigned(shift):
                self.assigned_shifts.append(shift)
                self.infeasible_shifts.remove(shift)
        for shift in self.assigned_shifts:
            if not self.is_feasible(shift):
                self.infeasible_shifts.append(shift)
                self.assigned_shifts.remove(shift)

class shift:
    def __init__(self, shift_id, location, date, start, to):
        self.id=shift_id
        self.date=date
        self.start=start
        self.to=to
        self.location=location
        self.assigned_vol=None
        
    def assign_volunteer(self, n_ass_vol):
        # remove old volunteer and update their availability
        shift_tup = (self.location, self.date, self.start, self.to)
        if self.assigned_vol:
            if shift_tup in self.assigned_vol.assigned_shifts:
                self.assigned_vol.assigned_shifts.remove(shift_tup)
            else:
                self.assigned_vol.infeasible_shifts.remove(shift_tup)
            self.assigned_vol.update_shift_feasibility()
        # add new volunteer and update their availaility
        res = n_ass_vol.assign_shift(shift_tup)
        n_ass_vol.update_shift_feasibility()
        self.assigned_vol = n_ass_vol
        return f'Shift covered by {n_ass_vol.name}' if res else f'Shift infeasibly assigned to {n_ass_vol.name}'
            
class shift_assignment:
    def __init__(self, shift_file_name, volunteer_filename):
        self.new_vols = []
        self.exp_vols = []
        self.shifts = []
        
        vol_table = pd.read_csv('Fringe_volunteer_master.csv', sep=';')
        shift_table = pd.read_csv('Fringe_shift_master.csv', sep=';')
        
        # read all volunteers and check their availability (X entire day, else from-to in hh:mm format)
        for _,row in vol_table.iterrows():
            vname = row[0]
            vexp = row[1]
            unav = row[2:]
            unav = unav.dropna()
            unav_l = []
            for ua in unav.iteritems():
                print(ua)
                udate = int(ua[0])
                if ua[1] == 'X':
                    unav_l.append((udate, '00:00', '23:59'))
                else:
                    tl = [(udate, ut.split('-')[0].strip(), ut.split('-')[1].strip()) for ut in ua[1].split(',')]
                    unav_l = unav_l + tl
            if vexp > 0:
                self.exp_vols.append(volunteer(vname, vexp, unav_l))
            else:
                self.new_vols.append(volunteer(vname, vexp, unav_l))
        
        # create all shifts to be filled
        for _, row in shift_table.iterrows():
            self.shifts.append(shift(row[4], row[0], int(row[1]), row[2], row[3]))
            
    def create_initial_assignment(self, care_exp=True):
        nshifts = len(self.shifts)
        nvols = len(self.new_vols) + len(self.exp_vols)
        shifts_per_vol = int(np.ceil(nshifts / nvols))
        # uncovered_shifts = self.shifts.copy()
        if care_exp:
            to_assign_exp = self.exp_vols*shifts_per_vol
            to_assign = self.new_vols*shifts_per_vol
        else:
            to_assign = (self.exp_vols+self.new_vols)*shifts_per_vol
        
        for sh in self.shifts:
            if care_exp:
                if sh.id == 'Vol1' and len(to_assign_exp) > 0:
                    v_to_assign = to_assign_exp.pop()
                    sh.assign_volunteer(v_to_assign)
                elif len(to_assign) > 0:
                    v_to_assign = to_assign.pop()
                    sh.assign_volunteer(v_to_assign)
                else:
                    v_to_assign = to_assign_exp.pop()
                    sh.assign_volunteer(v_to_assign)
            else:
                v_to_assign = to_assign.pop()
                sh.assign_volunteer(v_to_assign)
                
    def output_assignment(self):
        res = pd.DataFrame(columns=['location', 'date', 'from', 'to', 'id', 'volunteer'])
        for sh in self.shifts:
            sh_dict = {'location':[sh.location], 'date':[sh.date], 'from':[sh.start],
                       'to':[sh.to], 'id':[sh.id], 'volunteer':[sh.assigned_vol.name]}
            res = pd.concat([res, pd.DataFrame(sh_dict)])
        return res
                    