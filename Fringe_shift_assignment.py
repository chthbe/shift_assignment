# -*- coding: utf-8 -*-
"""
Created on Sat Jun  1 17:52:51 2024

@author: Christian Beckers chthbe@web.de
"""

import pandas as pd
import numpy as np

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
    def __init__(self, shift_file_name='Fringe_shift_master.csv', 
                 volunteer_filename='Fringe_volunteer_master.csv', care_exp=True):
        self.new_vols = []
        self.exp_vols = []
        self.shifts = []
        self.care_exp = care_exp
        
        vol_table = pd.read_csv(volunteer_filename, sep=';')
        shift_table = pd.read_csv(shift_file_name, sep=';')
        
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
            
    def create_initial_assignment(self):
        nshifts = len(self.shifts)
        nvols = len(self.new_vols) + len(self.exp_vols)
        shifts_per_vol = int(np.ceil(nshifts / nvols))
        # uncovered_shifts = self.shifts.copy()
        if self.care_exp:
            to_assign_exp = self.exp_vols*shifts_per_vol
            to_assign = self.new_vols*shifts_per_vol
        else:
            to_assign = (self.exp_vols+self.new_vols)*shifts_per_vol
        
        for sh in self.shifts:
            if self.care_exp:
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
        self.unassigned = to_assign
        if self.care_exp:
            self.unassigned_exp = to_assign_exp
                
    def output_assignment(self):
        res = pd.DataFrame(columns=['location', 'date', 'from', 'to', 'id', 'volunteer'])
        for sh in self.shifts:
            sh_dict = {'location':[sh.location], 'date':[sh.date], 'from':[sh.start],
                       'to':[sh.to], 'id':[sh.id], 'volunteer':[sh.assigned_vol.name]}
            res = pd.concat([res, pd.DataFrame(sh_dict)])
        return res
                    
    def fix_infeasible_shift_assignments(self):
        # returns True if all infeasible shifts could be fixed, else False
        res = True
        
        for sh in self.shifts:
            vol = sh.assigned_vol
            sh_tup = (sh.location, sh.date, sh.start, sh.to)
            if sh_tup in vol.infeasible_shifts:
                if self.care_exp:
                    sh_exp = sh.id == 'Vol1'
                    to_swap = []
                    # Check if previously unassigned volunteers can cover this shift
                    if sh_exp:
                        for ua in self.unassigned_exp:
                            if ua.is_feasible(sh_tup) and ua.is_unassigned(sh_tup):
                                to_swap = ua
                                break
                    else:
                        for ua in self.unassigned:
                            if ua.is_feasible(sh_tup) and ua.is_unassigned(sh_tup):
                                to_swap = ua
                                break
                    if to_swap != []:
                        # Found someone
                        sh.assign_volunteer(to_swap)
                        ua.append(vol)
                        continue
                    else:
                        # Found noone we need to swap shifts
                        found = False
                        visited = [vol]
                        all_vols = self.exp_vols if sh_exp else self.new_vols
                        p_swaps = [([vol], ps) for ps in np.setdiff1d(all_vols, visited)]
                        while not found:
                            npswaps = []
                            for pswap in p_swaps:
                                to_cover = [sh_tup] if pswap[0]==[vol] else pswap[0][-1].assigned_shifts + pswap[0][-1].infeasible_shifts
                                can_cover = False
                                for cover_sh in to_cover:
                                    if pswap[1].is_feasible(cover_sh) and pswap[1].is_unassigned(cover_sh):
                                        can_cover = True
                                        break
                                if can_cover: 
                                    for swap_sh in pswap[1].assigned_shifts + pswap[1].infeasible_shifts:
                                        if vol.is_feasible(swap_sh) and vol.is_unassigned(swap_sh):
                                            found = True
                                            swap_sh.assign_volunteer(vol)
                                            break
                                    if found:
                                        # We found a feasible swapping path
                                        print('Yay')
                                        path = pswap[0]+[pswap[1]]
                                        while len(path) > 2:
                                            shift_taker = path.pop()
                                            if path[-1] in self.unassigned:
                                                self.unassigned.remove(path[-1])
                                                self.unassigned.append(shift_taker)
                                            elif path[-1] in self.unassigned_exp:
                                                self.unassigned_exp.remove(path[-1])
                                                self.unassigned_exp.append(shift_taker)
                                            else:
                                                pot_shifts = path[-1].assigned_shifts + path[-1].infeasible_shifts
                                                for pot_sh in pot_shifts:
                                                    if shift_taker.is_feasible(pot_sh) and shift_taker.is_unassigned(pot_sh):
                                                        pot_sh.assign_volunteer(shift_taker)
                                                        break
                                        sh.assign_volunteer(path[1])
                                    else:
                                        # We need to search more
                                        visited.append(pswap[1])
                                        npswaps.append((pswap[0]+[pswap[1]], np.setdiff1d(all_vols, visited)))
                            # Checked all possibilities so far 
                            if set(visited)==set(all_vols):
                                # We could not find a feasible swap path
                                res = False
                                found = True
                                break
                            p_swaps = npswaps
                else:
                    # We do not care about experience
                    to_swap = []
                    # Check if previously unassigned volunteers can cover this shift
                    for ua in self.unassigned:
                        if ua.is_feasible(sh_tup) and ua.is_unassigned(sh_tup):
                            to_swap = ua
                            break
                    if to_swap != []:
                        # Found someone
                        sh.assign_volunteer(to_swap)
                        ua.append(vol)
                        continue
                    else:
                        # Found noone we need to swap shifts
                        found = False
                        visited = [vol]
                        all_vols = (self.new_vols + self.exp_vols)
                        p_swaps = [([vol], ps) for ps in np.setdiff1d(all_vols, visited)]
                        while not found:
                            npswaps = []
                            for pswap in p_swaps:
                                to_cover = [sh_tup] if pswap[0]==[vol] else pswap[0][-1].assigned_shifts + pswap[0][-1].infeasible_shifts
                                can_cover = False
                                for cover_sh in to_cover:
                                    if pswap[1].is_feasible(cover_sh) and pswap[1].is_unassigned(cover_sh):
                                        can_cover = True
                                        break
                                if can_cover: 
                                    for swap_sh in pswap[1].assigned_shifts + pswap[1].infeasible_shifts:
                                        if vol.is_feasible(swap_sh) and vol.is_unassigned(swap_sh):
                                            found = True
                                            swap_sh.assign_volunteer(vol)
                                            break
                                    if found:
                                        # We found a feasible swapping path
                                        print('Yay')
                                        path = pswap[0]+[pswap[1]]
                                        while len(path) > 2:
                                            shift_taker = path.pop()
                                            if path[-1] in self.unassigned:
                                                self.unassigned.remove(path[-1])
                                                self.unassigned.append(shift_taker)
                                            else:
                                                pot_shifts = path[-1].assigned_shifts + path[-1].infeasible_shifts
                                                for pot_sh in pot_shifts:
                                                    if shift_taker.is_feasible(pot_sh) and shift_taker.is_unassigned(pot_sh):
                                                        pot_sh.assign_volunteer(shift_taker)
                                                        break
                                        sh.assign_volunteer(path[1])
                                    else:
                                        # We need to search more
                                        visited.append(pswap[1])
                                        npswaps.append((pswap[0]+[pswap[1]], np.setdiff1d(all_vols, visited)))
                            # Checked all possibilities so far 
                            if set(visited)==set(all_vols):
                                # We could not find a feasible swap path
                                res = False
                                found = True
                                break
                            p_swaps = npswaps    
        return res