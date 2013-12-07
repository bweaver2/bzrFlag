#!/usr/bin/python -tt

# An incredibly simple agent.  All we do is find the closest enemy tank, drive
# towards it, and shoot.  Note that if friendly fire is allowed, you will very
# often kill your own tanks with this code.

#################################################################
# NOTE TO STUDENTS
# This is a starting point for you.  You will need to greatly
# modify this code if you want to do anything useful.  But this
# should help you to know how to interact with BZRC in order to
# get the information you need.
#
# After starting the bzrflag server, this is one way to start
# this code:
# python agent0.py [hostname] [port]
#
# Often this translates to something like the following (with the
# port name being printed out by the bzrflag server):
# python agent0.py localhost 49857
#################################################################

import sys
import math
import time
from numpy import *
from numpy.linalg import *
from operator import itemgetter, attrgetter

from bzrc import BZRC, Command

import OpenGL
OpenGL.ERROR_CHECKING = False
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from numpy import zeros

grid = None

def draw_grid():
    # This assumes you are using a numpy array for your grid
    width, height = grid.shape
    glRasterPos2f(-1, -1)
    glDrawPixels(width, height, GL_LUMINANCE, GL_FLOAT, grid)
    glFlush()
    glutSwapBuffers()

def update_grid(new_grid):
    global grid
    grid = new_grid



def init_window(width, height):
    global window
    global grid
    grid = zeros((width, height))
    glutInit(())
    glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_ALPHA | GLUT_DEPTH)
    glutInitWindowSize(width, height)
    glutInitWindowPosition(0, 0)
    window = glutCreateWindow("Grid filter")
    glutDisplayFunc(draw_grid)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    #glutMainLoop()

class kalmanAgent(object):
    """Class handles all command and control logic for a teams tanks."""
    ENEMY_TANK_MIN_DISTANCE = 1
    ENEMY_TANK_MAX_DISTANCE = 5
    OBSTACLE_MAX_DISTANCE = 10
    OBSTACLE_MIN_DISTANCE = 1
    BULLET_MAX_DISTANCE = 10
    BULLET_MIN_DISTANCE = 1
    FLAG_MIN_DISTANCE = 1
    FLAG_MAX_DISTANCE = 5
    FLAG_MAX_SPEED = 5
    PLOT_FILE = None
    WAYPOINTS_ARRAY = []
    CUR_WAYPOINT = [0,0,0,0]
    last_pos = []

    #Static variables for updating belief grid
    TRUE_HIT = 0.97
    TRUE_MISS = 0.9

    #Static Variables to store current perception of the map
    #map[0][0] = bottom left corner
    #map[800][0] = bottom righ corner
    #map[800][800] = top right corner
    baseBelief = 0.5
    beliefMap = [[baseBelief for x in xrange(800)] for x in xrange(800)]
    mu = array([[0],[0],[0],[0],[0],[0]])
    sigmaT = array([[100,0,0,0,0,0],
                    [0,0.1,0,0,0,0],
                    [0,0,0.1,0,0,0],
                    [0,0,0,100,0,0],
                    [0,0,0,0,0.1,0],
                    [0,0,0,0,0,0.1]])
    H = array([[1,0,0,0,0,0],
               [0,0,0,1,0,0]])
    H_tr = H.transpose()
    sigmaZ = array([[25,0],
                    [0,25]])
    dt = 0.5 #change in time between computations
    c = .1 #friction coeficient
    #assuming computations every 0.5 seconds
    F = array([[1,dt,(dt*dt)/2,0,0,0],
              [0,1, dt,  0,0, 0],
              [0,-c,1,   0,0, 0],
              [0,0, 0,   1,dt,(dt*dt)/2],
              [0,0, 0,   0,1, dt],
              [0,0, 0,   0,-c,1]])
    F_tr = F.transpose()

    sigmaX = array([[0.1,0,0,0,0,0],
                    [0,0.1,0,0,0,0],
                    [0,0,100,0,0,0],
                    [0,0,0,0.1,0,0],
                    [0,0,0,0,0.1,0],
                    [0,0,0,0,0,100]])


    last_posx = []
    last_posy = []
    last_ang = []
    time_to_print = 0
    
    def __updateKalman(self, z_next):
        F = self.F
        F_tr = self.F_tr
        H = self.H
        H_tr = self.H_tr
        sigmaT = self.sigmaT
        mu = self.mu
        sigmaX = self.sigmaX
        sigmaZ = self.sigmaZ

        k_in = F.dot(sigmaT).dot(F_tr)+sigmaX
        k_in2 = H.dot(k_in).dot(H_tr)+sigmaZ
        k_in3 = inv(k_in2)
        k_next = k_in.dot(H_tr).dot(k_in3)

        mu_in = z_next-H.dot(F).dot(mu) 
        mu_next = F.dot(mu) + k_next.dot(mu_in)
        sigmaT_next = ((identity(6)-k_next.dot(H)).dot(k_in))
        print sigmaT_next

        self.sigmaT = sigmaT_next
        self.mu = mu_next
        return H.dot(self.mu), self.sigmaT

    def __init__(self, bzrc):
        self.bzrc = bzrc
        self.constants = self.bzrc.get_constants()
        if self.constants['truepositive']:
            TRUE_HIT = self.constants['truepositive']
            print 'new true hit:', TRUE_HIT
        if self.constants['truenegative']:
            TRUE_MISS = self.constants['truenegative']
            print 'new true mess:', TRUE_MISS
        self.commands = []
        self.PLOT_FILE = bzrc.get_plot_file()
        self.base = None
        self.time_to_print = 20
        bases = self.bzrc.get_bases()
        for base in bases:
            if base.color == self.constants['team']:
                self.base = base
        mytanks, othertanks, flags, shots = self.bzrc.get_lots_o_stuff()
        obstacles = self.bzrc.get_obstacles()
        self.last_posx = []
        self.last_posy = []
        self.last_pos = []
        self.WAYPOINTS_ARRAY = [
            [[-350,350],   [-175,350], [0,350], [175,350],  [350,350], 
                [350,250], [175,250],  [0,250], [-175,250], [-350,250]],  #Tank 1
            [[-350,150],   [-175,150], [0,150], [175,150],  [350,150], 
                [350,50],  [175,50],   [0,50],  [-175,50],  [-350,50]],   #Tank 2
            [[-350,-50],   [-175,-50], [0,-50], [175,-50],  [350,-50], 
                [350,-150],[175,-150], [0,-150],[-175,-150],[-350,-150]], #Tank 3
            [[-350,-250],  [-175,-250],[0,-250],[175,-250], [350,-250],
                [350,-350],[175,-350], [0,-350],[-175,-350],[-350,-350]]  #Tank 4
            ]
        self.last_ang = []
        for tank in mytanks:
            self.last_posx.append(tank.x-0)
            self.last_posy.append(tank.y-0)
            self.last_ang.append(tank.angle-0)
            self.last_pos.append([tank.x,tank.y])

    

    def updateBelief(self, pos, noise):

        x = int(pos[0][0]) + 400
        y = (int(pos[1][0]) + 400)

        #print the center of the belief
        self.beliefMap[x][y] = 1

        #print the certainty ring around it at one standard deviation
        x_noise = noise[0][0]
        y_noise = noise[3][3]
        #print x,y,x_noise,y_noise
        #float[] a = new float[3*361]; // 3-coordinates and 361 angles
        for i in xrange(360):
            c_x = int(x+math.cos(i*math.pi/180)*x_noise)
            c_y = int(y+math.sin(i*math.pi/180)*y_noise)

            if c_x < 0 or c_x >= 800 or c_y < 0 or c_y >= 800:
                pass
            else:
                #print c_x,c_y
                #the ring is going to be black
                self.beliefMap[c_x][c_y] = 0

    
    def get_observations(self):
        enemies = self.bzrc.get_othertanks()
        for tank in enemies:
            print tank.color
            if tank.color == 'blue':
                #we only get tank positions
                return array([[tank.x],[tank.y]])

    def clear_belief_map(self):
        self.beliefMap = [[self.baseBelief for x in xrange(800)] for x in xrange(800)]

    def tick(self, time_diff):
        """Some time has passed; decide what to do next."""
        z_next = self.get_observations()
        self.clear_belief_map();
        

        pos, noise = self.__updateKalman(z_next);
        self.updateBelief(pos, noise)




    def normalize_angle(self, angle):
        """Make any angle be between +/- pi."""
        angle -= 2 * math.pi * int (angle / (2 * math.pi))
        if angle <= -math.pi:
            angle += 2 * math.pi
        elif angle > math.pi:
            angle -= 2 * math.pi
        return angle



    def should_shoot(self, tank, flags, shots, obstacles):
        return True

def main():
    # Process CLI arguments.
    try:
        execname, host, port = sys.argv
    except ValueError:
        execname = sys.argv[0]
        print >>sys.stderr, '%s: incorrect number of arguments' % execname
        print >>sys.stderr, 'usage: %s hostname port' % sys.argv[0]
        sys.exit(-1)

    # Connect.
    #bzrc = BZRC(host, int(port), debug=True)
    bzrc = BZRC(host, int(port))

    agent = kalmanAgent(bzrc)

    init_window(800,800)
    # Run the agent
    try:
        tickCounter = 0
        prev_time = time.time()
        while True:
            time_diff = time.time() - prev_time
            prev_time = time.time()
            agent.tick(time_diff)
            if tickCounter % 10 == 0:
                draw_grid()
                update_grid(array(zip(*agent.beliefMap)))
                #update_grid(numpy.array(agent.beliefMap))
            tickCounter = tickCounter + 1
    except KeyboardInterrupt:
        print "Exiting due to keyboard interrupt."
        bzrc.close()


if __name__ == '__main__':
    main()

# vim: et sw=4 sts=4
