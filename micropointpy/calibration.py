from micropoint import Micropoint
import time
import sys
import os
from os.path import isfile, join, dirname
import json
import time

def get_dice(dice_top_left=[0,0], spacing=1):
    dice = {1:[[2,2]],2:[[0,4],[4,0]],3:[[0,4],[2,2],[4,0]],4:[[0,0],[0,4],[4,0],[4,4]],5:[[0,0],[0,4],[2,2],[4,0],[4,4]],6:[[0,0],[0,2],[0,4],[4,0],[4,2],[4,4]]}
    for key in dice.keys():
    	points = dice[key]
    	points_out = [[x*spacing+dice_top_left[0],y*spacing+dice_top_left[1]] for x,y in points]
    	dice[key] = points_out
    return dice

def get_calibration_positions(cal_range=256,sampling=8,offset=0):
    positions = []
    for i in range(0, sampling+1):
      for j in range(0, sampling+1):
        x = cal_range/sampling*i+offset
        y = cal_range/sampling*j+offset
        if x == 256:
            x = 255
        if y == 256:
            y = 255
        positions.append([x,y])
    return  positions

def get_power_strip(fixed=64, start=79, end=178,spacing=3,axis=0):
    if start>end:
        x = list(reversed(range(end, start, spacing)))
    else:
        x = range(start,end,spacing)
    y = [fixed]*len(x)
    if axis==0:
        strip = list(zip(x,y))
    if axis==1:
        strip = list(zip(y,x))
    return strip

def write_mp_file(roi,fnum,reps=2,atten=55,sampling=1,roi_type='SHAPE', run_uncal=True, no_wait=False):
    to_write = {'ROIS': [[roi]], 'ROITypes': [roi_type], 'Settings': [{'reps': reps, 'atten': atten, 'sampling': sampling, 'no_wait': False, 'run_uncal':run_uncal}]}
    with open('%03d-%d-%d.json'%(fnum,roi[0],roi[1]),'w+') as out_f: 
        out_f.write(json.dumps(to_write))
    with open('Calibration-file-list.csv', 'a+') as out_f:
        if fnum == 0:
            linestart = ""
        else:
            linestart = "\n"
        out_f.write('%s%03d-%d-%d.json,%d,%d,%d'%(linestart,fnum,roi[0],roi[1],fnum,roi[0],roi[1]))
    return to_write


mp = Micropoint()
mp.set_attenuator(60)
points = [[192,64],[192,128],[192,192],[64,192],[64,128],[64,64]]
x_offset = 0
y_offset = 0
points = [[x+x_offset,y+y_offset] for x,y in points]
i=0
fnum = 0

for point in points:
    dice = get_dice(point, spacing=2)
    print(dice)
    i+=1
    for x,y in dice[i]:
        mp.point_fire(x,y,uncal=True)

for point in get_calibration_positions():
    write_mp_file(point,fnum)
    fnum += 1

points = get_power_strip()
powers  = range(0,90)
power_strips = [(182,178,79,3,0),(128,178,79,3,1),(74,79,178,3,0)]
i=0
for strip in power_strips:
    points = get_power_strip(*strip)
    points.pop(int((len(points)-1)/2))
    points.pop(-1)
    points.pop(0)
    for x,y in points:
        try:
            mp.set_attenuator(powers[i])
            mp.point_fire(x,y,uncal=True)
            print('x=%d,y=%d,p=%d'%(x,y,powers[i]))
            i+=1
        except:
            continue