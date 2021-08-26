from micropoint import Micropoint
import time
import sys
import os
from os.path import isfile, join, dirname
import json

def get_size(path):
    if type(path) is not str:
        path = str(path)
    return os.stat(path).st_size

def get_mtime(path):
    if type(path) is not str:
        path = str(path)
    return os.stat(path).st_mtime

def watch_modified(path, delay=0.1, size=False, mtime=False):
	if not size:
		size = get_size(path)
	if not mtime:
		mtime = get_mtime(path)
	while size==get_size(path) and mtime==get_mtime(path):
		time.sleep(delay)
	return get_mtime(path)

def open_safe(path, method='a'):
    result = None
    while result is None:
        try:
            return open(path, method)
        except:
            pass

def getFiles(mypath,suffix=''):
    return [f for f in os.listdir(mypath) if (isfile(join(mypath, f)) and f.endswith(suffix))]

def get_settings(sets,cur_settings, mp):
    # sets = settings[0]
    if sets.get('reps'):
        mp.reps = sets.get('reps')
        cur_settings["reps"] = sets.get('reps')
    if (sets.get('atten') and mp.attenuator_position!=sets.get('atten')):
        mp.set_attenuator(sets.get('atten'))
        cur_settings["atten"] = sets.get('atten')
    # Should points be run without calibration
    try:
        cur_settings["run_uncal"] = sets.get('run_uncal')
    except:
        print("Couldn't find run_uncal setting.")
    cur_settings["sampling"] = sets.get('sampling')
    cur_settings["no_wait"] = sets.get('no_wait')
    return cur_settings

def get_parent(path, level=1):
	return dirname(path)

def touch(path):
        basedir = get_parent(path)
        try:
            if not os.path.exists(basedir):
                os.makedirs(basedir)
        except OSError:
            pass
        with open(path, 'a'):
            os.utime(path, None)
        return path
    
def watch_rois(inpath,delay=0.1,cur_settings={"reps":1,"atten":58,"samplng":1,"run_uncal":False,"roi_type":'SHAPE','no_wait':False}):
    inpath = "H:\\Data\\Francois\\rois\\" #Changed to my folder (Jason)
    leave_continue = True #Leave a continue.temp file in the watch folder.
    continue_file = os.path.join(inpath,'continue.temp')
    mp = Micropoint()
    time.sleep(5)
    mp.find_attenuator_position()
    # time.sleep(5)
    mp.set_attenuator(cur_settings['atten'])
    live = True
    oldFiles = getFiles(inpath,'.json')
    print('Repititions =\t%d' %mp.reps)
    used_dir = os.path.join(inpath,'Used')
    unused_dir = os.path.join(inpath,'Unused')
    if not os.path.exists(used_dir):
        os.makedirs(used_dir)
    if not os.path.exists(unused_dir):
        os.makedirs(unused_dir)
    while live:
        t1 = watch_modified(inpath, delay=delay)
        print('%s was modified at %s' %(str(inpath), str(t1)))
        currentFiles = getFiles(inpath,'.json')
        newFiles = [i for i in currentFiles if i not in oldFiles]
        print(newFiles)
        oldFiles = currentFiles
        if len(newFiles)>0:
            newFiles = [(i,get_mtime(os.path.join(inpath,i))) for i in newFiles]
            if len(newFiles)>1:
                newFiles.sort(key=lambda tup: tup[1], reverse=True)
            print(newFiles)
            for f in newFiles:
                print(f[0])
                if 'exit-mp' in f[0]:
                    live = False
                    print('Closing ROI watcher.')
            if live:
                time.sleep(0.1)
                print(newFiles)
                with open(os.path.join(inpath, newFiles[0][0]),'r') as f:
                    try: container = json.load(f)
                    except: continue
                print(container)
                rois = container.get('ROIS')
                roitypes = container.get('ROITypes')
                settings = container.get('Settings')
                if settings:
                    cur_settings = get_settings(settings[0],cur_settings, mp)
                for i in range(len(rois)):
                    if len(settings)>i:
                        cur_settings = get_settings(settings[i],cur_settings, mp)
                    if len(roitypes)>=i:
                        cur_settings['roi_type'] = roitypes[i]
                    print(cur_settings['roi_type'])
                    current_roi = rois[i]
                    if cur_settings['roi_type'] == 'FILL':
                        # current_roi = mp.to_galvo_polygon(current_roi)
                        if not cur_settings["no_wait"]:
                            pass
                        # print(current_roi)
                        current_roi = mp.polygon_fill(current_roi,uncal=cur_settings["run_uncal"],sampling=cur_settings["sampling"], points_only=True)
                        cur_settings["run_uncal"] = True
                        print('Current sampling = %d' %cur_settings['sampling'])
                        # print(current_roi)
                    # else:
                    ts = time.time()
                    if not cur_settings["no_wait"]:
                        pass
                    for (x,y) in current_roi:
                        print('Firing\t%d\t%d'%(x,y))
                        mp.point_fire(int(x),int(y), uncal=cur_settings["run_uncal"])
                    tot_time = time.time()-ts
                    print(tot_time)
                    if tot_time>0:
                        print('Fired %d times in %d seconds.\n%dHz' %(len(current_roi),tot_time, len(current_roi)/tot_time))
                    else:
                        print('Fired %d times in %d seconds.\n~inf Hz' %(len(current_roi),tot_time))
                if leave_continue:
                    touch(continue_file)
                os.rename(os.path.join(inpath,newFiles[0][0]),os.path.join(used_dir,str(time.time())+'_'+newFiles[0][0]))

if __name__ == '__main__':
    args = sys.argv
    if len(args)>1:
        inpath = args[1]
        try:
            opt = json.loads(sys.argv[2])
        except:
            opt = False
        if opt:
            watch_rois(inpath=inpath,cur_settings=opt)
        else:
            watch_rois(inpath=inpath)
        print("Fin.")
    else:
        print("No arguments provided.\nPlease provide a directory, and (optionally) json formatted current setitngs.\nDefault settings of form:{'reps':1,'atten':58,'samplng':1,'run_uncal':False,'roi_type':'SHAPE','no_wait':False}")
    