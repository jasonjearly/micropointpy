import serial
import time
import numpy as np
from matplotlib import path
import os
import time
import math
import json

class Micropoint:
    def __init__(self, config_path=False, port='COM12'):
        if not config_path:
            config_path = os.path.join(os.path.expanduser('~'),'.micropointpy','cal')
        self.calFile = os.path.join(config_path,'MicroPoint-Calibration.npy')
        self.offsetFile = os.path.join(config_path,'Offset-Calibration.json')
        if not os.path.exists(self.offsetFile):
            self.x_offset = 0
            self.y_offset = 0
        else:
            try:
                with open(self.offsetFile,'r') as f:
                    offset_info = json.load(f)
                self.x_offset = int(offset_info['x'])
                self.y_offset = int(offset_info['y'])
            except Exception as e:
                print('Could not set offset.')
                print(e)
                self.x_offset = 0
                self.y_offset = 0
        self.calibration = 0
        self.load_cal(self.calFile)
        self.port = port
        self.baud = '9600'
        self.timeout = 0.01
        self.mp = self.micropoint()
        self.reps = 1
        self.fire_delay = 1.0/16
        self.x = 0
        self.y = 0
        self.configure_port()
        self.attenuator_position = None
        self.find_attenuator_position()
        time.sleep(1)
        #self.attenuator_position = self.find_attenuator_position()

    def micropoint(self):
        ser = serial.Serial(
            port=self.port,
            baudrate=self.baud,
            parity='N',
            timeout=self.timeout
        )
        return ser

    def write_bytes(self, b, timeout=0.05,out=0):
        if len(b)==1:
            to_write = b
            # print(to_write)
        elif len(b)>1:
            to_write = b''.join(b)
        else:
            print('No bytes provided to write to device.')
            return 0
        # print('Writing: %s' %to_write)
        self.mp.write(to_write)
        if timeout:
            time.sleep(timeout)
        if out:
            return self.read_bytes(out)

    def read_bytes(self, length):
        return self.mp.read(size=length)

    def configure_port(self):
        #print(self.write_bytes(bytearray(['!','A',0]),out=3))
        #print(self.write_bytes(bytearray(['!','B',0]),out=3))
        #print(self.write_bytes(bytearray(['!','C',16+8+4]),out=3))
        ret = self.write_bytes((b'!',b'A',bytes([0])),out=3)
        if ret != b'':
            print('!A')
            return ret
        ret = self.write_bytes((b'!',b'B',bytes([0])),out=3)
        if ret != b'':
            print('!B')
            return ret
        ret = self.write_bytes((b'!',b'C',bytes([16+8+4])),out=3)
        if ret != b'':
            print('!C')
            return ret
        print('Port directions configured.')

    def set_illumination(self, on=True):
        if on:
            self.write_bytes((b'C',bytes([0x02]),b'C',bytes([0x00])),timeout=self.fire_delay)

    def point(self,x,y,uncal=False):
        if not uncal:
            loc = self.img2galvo(x,y)
            x = int(loc[0])
            y = int(loc[1])
        print('x=%s,y=%s'%(x,y))
        x = x+self.x_offset
        y = y+self.y_offset
        print('x=%s,y=%s'%(x,y))
        if 0<=x<=255 and 0<=y<=255:
            self.write_bytes((b'A',bytes([x]),b'B',bytes([y])))
        self.x = x
        self.y = y

    def fire(self):
        for i in range(self.reps):
            self.set_illumination(True)

    def point_fire(self, x, y, uncal=False):
        self.point(x,y,uncal)
        if 0<=self.x<=255 and 0<=self.y<=255:
            for i in range(self.reps):
                self.set_illumination(True)
        else:
            print('Out of range of MP')

    def is_attenuator_home(self):
        test = self.write_bytes((b'c'), timeout=0.05, out=1)
        print(test)
        return(b'\x14' in test)

    def is_attenuator_home2(self):
        test = self.write_bytes((b'c'), timeout=0, out=10)
        return(test)

    def step_attenuator(self, direction):
        if direction:
            out = self.write_bytes((b'C',bytes([0xc0]),b'C',bytes([0x00])))
        else:
            out = self.write_bytes((b'C',bytes([0x80]),b'C',bytes([0x00])))
        return out

    def move_attenuator(self, steps):
        if not steps:
            return False
        self.write_bytes((b'A',bytes([0x00]),b'B',bytes([0x00])))
        direction = 1
        if steps < 0:
            direction = 0
            steps = steps*-1
        for i in range(steps):
            self.step_attenuator(direction)
        return True

    def set_attenuator(self, pos):
        if 0 <= pos <= 89:
            self.move_attenuator(pos-self.attenuator_position)
            self.attenuator_position = pos

    def find_attenuator_position(self):
        start = 0
        print('Finding attenuator home position.')
        while not self.is_attenuator_home() and start < 100:
            self.step_attenuator(0)
            start += 1
        if not self.is_attenuator_home():
            return -1
        if not start:
            count = 0
            while self.is_attenuator_home() and count < 100:
                self.step_attenuator(1)
                if count == 99:
                    return -1
                count += 1
            self.step_attenuator(0)
        self.move_attenuator(start)
        self.attenuator_position = start
        print('Attenuator is set to %d = %.4g%%' %(self.attenuator_position, self.percent_attenuator(self.attenuator_position)))
        return start

    def percent_attenuator(self, n):
        return 0.1*1000.0**(n/89.0)

    def int_attenuator(self, n):
        #Based on https://www.mathpapa.com/algebra-calculator.html
        if n:
            return round(math.log10(n*10)/math.log10(1000)*89)
        return -1

    def img2galvo(self, x,y):
        pad = lambda g: np.hstack([g, np.ones((g.shape[0],1))])
        unpad = lambda g: g[:,:-1]
        transform = lambda g: unpad(np.dot(pad(g), self.calibration))
        out = transform(np.array([[x,y]]))
        out2 = [round(out[0][0],0),round(out[0][1],0)]
        return out2

    def make_cal(self, in_p, out_p):
        if type(in_p) != np.ndarray:
            in_p = np.asarray(in_p)
            out_p = np.asarray(out_p)
        pad = lambda x: np.hstack([x, np.ones((x.shape[0],1))])
        # unpad = lambda x: x[:,:-1]
        X = pad(in_p)
        Y = pad(out_p)
        A, res, rank, s = np.linalg.lstsq(X, Y, rcond=-1)
        return A
    
    def transform_xy(self, x,y, cal):
        pad = lambda g: np.hstack([g, np.ones((g.shape[0],1))])
        unpad = lambda g: g[:,:-1]
        transform = lambda g: unpad(np.dot(pad(g), cal))
        out = transform(np.array([[x,y]]))
        out2 = [round(out[0][0],0),round(out[0][1],0)]
        return out2

    def to_galvo_polygon(self, roi):
        if len(self.calibration) != 0:
            roi = [self.img2galvo(i[0],i[1]) for i in roi]
        #    for i in roi:
        #        for n in range(i):
        #            i[n] = img2galvo(i[n])
        return roi

    def polygon_fill(self, roi, uncal=False, sampling=1, points_only=False):
        if not uncal:
            roi = [self.img2galvo(x,y) for x,y in roi]
        points = self.contained_points(roi,sampling)
        if not points_only:
            for point in points:
                self.point_fire(int(point[0]),int(point[1]),uncal=True)
        return points

    def load_cal(self, file):
        self.calibration = np.load(file)

    def boundingbox(self, roi):
        arr = np.array(roi)
        mins = []
        maxs = []
        for i in range(len(roi[0])-1,len(roi[0])+1):
            mins.append(min(arr[:,i-1:i])[0])
            maxs.append(max(arr[:,i-1:i])[0])
        return([mins,maxs])

    def is_within(self, roi, point):
        p = path.Path(roi)
        return p.contains_point(point, transform=None)

    def are_within(self, roi,points):
        p = path.Path(roi)
        return p.contains_points(points, transform=None)

    def contained_points(self, roi, step=1):
        box = self.boundingbox(roi)
        mins = box[0]
        maxs = box[1]
        # box_coord = [[mins[0],mins[1]],[maxs[0],mins[1]],[maxs[0],maxs[1]],[mins[0],maxs[1]]]
        ac = np.meshgrid(range(int(mins[0]),int(maxs[0]), step),range(int(mins[1]),int(maxs[1]), step))
        ac = np.append(ac[0].reshape(-1,1),ac[1].reshape(-1,1),axis=1)
        m = self.are_within(roi,ac)
        return [ac[i] for i in range(len(ac)) if m[i]]
