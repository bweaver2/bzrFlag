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
import numpy
from numpy import *
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

class basicAgent(object):
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


    last_posx = []
    last_posy = []
    last_ang = []
    time_to_print = 0

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

    def updateBelief(self, tank):
        pos, grid = self.bzrc.get_occgrid(tank.index)

        #map coordinates are centered at 0,0; top left corner is -400, 400, top right is 400, 400, etc
        #always use given position, never the tanks position
        #position gives bottom left corner of array
        #buf = "grid x dim %d, grid y dim %d\n" % (len(grid),len(grid[0]))
        #print buf
        for relativeX in xrange(len(grid)):
            for relativeY in xrange(len(grid[0])):
                SensorX = relativeX + pos[0] + 400
                SensorY = relativeY + pos[1] + 400
                if SensorX < 0 or SensorY < 0 or SensorX >= 800 or SensorY >= 800:
                    continue
                occupied = grid[relativeX][relativeY]
                prior = self.beliefMap[SensorX][SensorY]
                if occupied == 1:
                    # Recall that p(SensorX,SensorY) is the probability that a cell is occupied
                    Bel_Occ = self.TRUE_HIT * prior;
                    # So 1-p(SensorX,SensorY) is the probability that a cell is unoccupied
                    Bel_Unocc = (1 - self.TRUE_MISS) * (1 - prior);
                    #now we normailze
                    self.beliefMap[SensorX][SensorY] = Bel_Occ / (Bel_Occ + Bel_Unocc);
                else:
                    # Recall that p(SensorX,SensorY) is the probability that a cell is occupied
                    Bel_Occ = (1 - self.TRUE_HIT) * prior;
                    # So 1-p(SensorX,SensorY) is the probability that a cell is unoccupied
                    Bel_Unocc = self.TRUE_MISS * (1 - prior);
                    #now we normailze
                    self.beliefMap[SensorX][SensorY] = Bel_Occ / (Bel_Occ + Bel_Unocc);

    def tick(self, time_diff):
        """Some time has passed; decide what to do next."""
        mytanks, othertanks, flags, shots = self.bzrc.get_lots_o_stuff()
        obstacles = self.bzrc.get_obstacles()
        self.mytanks = mytanks
        self.othertanks = othertanks
        self.flags = flags
        self.shots = shots
        self.enemies = [tank for tank in othertanks if tank.color !=
                        self.constants['team']]
        self.friendlies = [tank for tank in othertanks if tank.color ==
                        self.constants['team']]
        self.obstacles = obstacles

        self.commands = []
        curTanks = [mytanks[0]]
        curTanks.extend(mytanks[:4])
        if self.time_to_print < 0 :
			self.time_to_print = 20
        self.time_to_print = self.time_to_print - time_diff

        "we need a new speed, a new angle, and whether or not to shoot"
        for tank in curTanks:
            self.updateBelief(tank)
            x = tank.x
            y = tank.y
            tankWayPointIndex = self.CUR_WAYPOINT[tank.index]
            tankWayPoints = self.WAYPOINTS_ARRAY[tank.index]
            if tankWayPointIndex < len(tankWayPoints):
                speed, angle = self.get_desired_movement(tank, flags, shots, obstacles)
                shoot = self.should_shoot(tank, flags, shots, obstacles)
                if time_diff > 0:
                    velx = (tank.x-self.last_posx[tank.index])/time_diff
                    vely = (tank.y-self.last_posy[tank.index])/time_diff
                    veltheta = abs((tank.angle-self.last_ang[tank.index])/time_diff)
                else:
                    velx = 0
                    vely = 0
                    veltheta = 0
                deltaX = float(speed * math.cos(angle))
                deltaY = float(speed * math.sin(angle))
                if self.time_to_print < 0:
                    self.PLOT_FILE.write("%s %s %s %s\n" % (x, y, deltaX, deltaY))
            
                speed = speed - .001*((velx**2+vely**2)**.5)
                speed = min(speed,1)
                shoot = self.should_shoot(tank, flags, shots, obstacles)
                if angle > 0 :
                    angle = angle - .000001*veltheta
                    angle = min(angle,1)
                    command = Command(tank.index, speed, angle, shoot)
                elif angle < 0:
                    angle = angle+.000001*veltheta
                    angle = max(angle,-1)
                    command = Command(tank.index, speed, angle, shoot)
                else:
                    command = Command(tank.index, speed, 0, shoot)
                self.commands.append(command)
                
                rangeCheck = 10
                """
                print tank.x-self.last_posx[tank.index], tank.y-self.last_posy[tank.index], time_diff
                if ((tank.x-self.last_posx[tank.index]) == 0.0) and ((tank.y-self.last_posy[tank.index]) == 0.0) and time_diff > .1:
                    newPoint = [0,0]
                    tankx = int(math.floor(tank.x))
                    tanky = int(math.floor(tank.y))
                    while newPoint[0] < 10 and newPoint[1] < 10 and self.beliefMap[newPoint[0]+tankx][newPoint[1]+tanky] !=0:
                        newPoint[0] = random.randint(-50, 50)
                        newPoint[1] = random.randint(-50, 50)
                        #if self.beliefMap[]
                    newPoint[0] = newPoint[0] + tankx
                    newPoint[1] = newPoint[1] + tanky
                    print 'random', newPoint
                    tankWayPoints.insert(tankWayPointIndex, newPoint)
                """
                stuck = self.is_tank_stuck(tank)
                #print 'current goal', tankWayPoints[tankWayPointIndex], [tank.x, tank.y]
                if stuck:
                    stuck = False
                    #print 'stuck!'
                    newWayPoints = self.get_closest_reachable_gray(tank, tankWayPoints[tankWayPointIndex]);
                    #print newWayPoints
                    if newWayPoints:
                        self.WAYPOINTS_ARRAY[tank.index] = newWayPoints + self.WAYPOINTS_ARRAY[tank.index]

                if x > tankWayPoints[tankWayPointIndex][0]-rangeCheck and x < tankWayPoints[tankWayPointIndex][0]+rangeCheck:
                    if y > tankWayPoints[tankWayPointIndex][1]-rangeCheck and y < tankWayPoints[tankWayPointIndex][1]+rangeCheck:
                        self.CUR_WAYPOINT[tank.index] = tankWayPointIndex + 1
            #else we start over
            else:
                self.CUR_WAYPOINT[tank.index] = 0
            self.last_posx[tank.index] = tank.x
            self.last_posy[tank.index] = tank.y
        results = self.bzrc.do_commands(self.commands)

    def is_tank_stuck(self, tank):
        # a tank is stuck if the path in fron of it is occupied (wall, other tanks)
        tankx = int(tank.x) + 400
        tanky = int(tank.y - 400) * -1
        othertanks = self.bzrc.get_othertanks()
        mytanks = self.bzrc.get_mytanks()
        tankWayPointIndex = self.CUR_WAYPOINT[tank.index]
        tankWayPoints = self.WAYPOINTS_ARRAY[tank.index]

        #check for friendly tank
        for nextTank in mytanks:
            if tank.index != nextTank.index:
                dist = math.sqrt((nextTank.x - tank.x)**2 + (nextTank.y - tank.y)**2)
                if dist < 1:
                    return True

        #check for enemy tank
        for nextTank in othertanks:
            dist = math.sqrt((nextTank.x - tank.x)**2 + (nextTank.y - tank.y)**2)
            if dist < 1:
                return True

        x_point = int(math.ceil(tankx - 10*cos(tank.angle)))
        y_point = int(math.ceil(tanky - 10*sin(tank.angle)))
        if self.beliefMap[x_point][y_point] > .9:
            ang1 = math.atan2(y_point + (tanky),x_point - (tankx))
            ang2 = math.atan2(tankWayPoints[tankWayPointIndex][1]-int(tank.y),tankWayPoints[tankWayPointIndex][0]-int(tank.x))
            #                    print ang1, ang2
            if ang1 +math.pi/4 > ang2 and ang1-math.pi/4 < ang2:
                print 'stuck'
                return True

        '''
        #check for wall
        white_threshold = .9
        for i in xrange(-1, 2):
            for j in xrange(-1, 2):
                if not (i == 0 and j == 0):
                    checkx = i + tankx
                    checky = j + tanky
                    #check if if the values are on the map and unvisited
                    if checkx >= 0 and checkx < 800 and checky >= 0 and checky < 800:
                        if self.beliefMap[checkx][checky] >= white_threshold:
                            return True
        '''




    def normalize_angle(self, angle):
        """Make any angle be between +/- pi."""
        angle -= 2 * math.pi * int (angle / (2 * math.pi))
        if angle <= -math.pi:
            angle += 2 * math.pi
        elif angle > math.pi:
            angle -= 2 * math.pi
        return angle

    def get_desired_movement(self, tank, flags, shots, obstacles):
        final_angle = 0
        final_speed = 0
        vectors = []
        #vectors.extend(self.get_repulsive_vectors(tank, shots))
        vectors.extend(self.get_attractive_vectors(tank, flags))
        #vectors.extend(self.get_tangential_vectors(tank, obstacles))
        for speed, angle in vectors:
            final_speed += speed
            final_angle += angle
        return final_speed, final_angle

    def get_repulsive_vectors(self, tank, shots):
        speeds = []
        angles = []
        
        #lab 1
        #obstacles like walls are interesting, we can't define them as points so we need to be a little more specific
        #each obstacle is a set of 4 points defining a rectangle
        """for obstacle in obstacles:
            intersection = self.will_hit_obstacle(tank, obstacle)
            if intersection != None:
                #we are only applying tangential forces
                dist = math.sqrt((intersection[0] - tank.x)**2 + (intersection[1] - tank.y)**2)
                if self.OBSTACLE_MIN_DISTANCE < dist < self.OBSTACLE_MAX_DISTANCE:
                    target_angle = math.atan2(intersection[1] - tank.y, intersection[0] - tank.x)
                    tangent_angle = self.normalize_angle(target_angle + 180)
                    relative_angle = self.normalize_angle(tangent_angle - tank.angle)
                    speeds.append(-1/dist)
                    angles.append(tangent_angle)
        """
        #lab2
        return zip(speeds, angles)

    def hasFlag(self,tank,flags):
        for flag in flags:
            if tank.flag == flag:
                return True;
        return False;

    def get_attractive_vectors(self, tank, flags):
        speeds = []
        angles = []
        speed = 0
        angle = 0
        bestFlag = None
        bestDist = None
        
        #lab 1
        """for flag in flags:
            
            if (tank.flag == "-" and flag.color != self.constants['team'] and flag.poss_color != self.constants['team']):
                dist = math.sqrt((flag.x - tank.x)**2 + (flag.y - tank.y)**2)
                if bestDist == None or dist < bestDist:
                    bestFlag = flag
                    bestDist = dist
                    target_angle = math.atan2(flag.y - tank.y, flag.x - tank.x)
                    relative_angle = self.normalize_angle(target_angle - tank.angle)
                    if dist > self.FLAG_MAX_DISTANCE:
                        speed = self.FLAG_MAX_SPEED
                        angle = relative_angle
                    elif dist > self.FLAG_MIN_DISTANCE:
                        speed = dist
                        angle = relative_angle
            elif (tank.flag != "-" and flag.color != self.constants['team']):
                #run home depo
                target_angle1 = math.atan2(self.base.corner1_y - tank.y, self.base.corner1_x - tank.x)
                target_angle2 = math.atan2(self.base.corner2_y - tank.y, self.base.corner2_x - tank.x)
                target_angle3 = math.atan2(self.base.corner3_y - tank.y, self.base.corner3_x - tank.x)
                target_angle4 = math.atan2(self.base.corner4_y - tank.y, self.base.corner4_x - tank.x)
                
                relative_angle1 = self.normalize_angle(target_angle1 - tank.angle)
                relative_angle2 = self.normalize_angle(target_angle2 - tank.angle)
                relative_angle3 = self.normalize_angle(target_angle3 - tank.angle)
                relative_angle4 = self.normalize_angle(target_angle4 - tank.angle)
                
                speeds.extend([5,5,5,5])
                angles.extend([relative_angle1,relative_angle2,relative_angle3,relative_angle4])
        """
        #lab 2

        tankWayPointIndex = self.CUR_WAYPOINT[tank.index]
        tankWayPoints = self.WAYPOINTS_ARRAY[tank.index]


        dist = math.sqrt((tankWayPoints[tankWayPointIndex][0] - tank.x)**2 + (tankWayPoints[tankWayPointIndex][1] - tank.y)**2)
        target_angle = math.atan2(tankWayPoints[tankWayPointIndex][1] - tank.y, tankWayPoints[tankWayPointIndex][0] - tank.x)
        relative_angle = self.normalize_angle(target_angle - tank.angle)
        if dist >= self.FLAG_MAX_DISTANCE:
            speed = self.FLAG_MAX_SPEED
        elif dist >= self.FLAG_MIN_DISTANCE:
            speed = 1
        angle = relative_angle
        speeds.append(speed)
        angles.append(angle)
        return zip(speeds, angles)

    def get_tangential_vectors(self, tank, obstacles):
        speeds = []
        angles = []
        #lab1
        """
        #obstacles like walls are interesting, we can't define them as points so we need to be a little more specific
        #each obstacle is a set of 4 points defining a rectangle
        for obstacle in obstacles:
            intersection = self.will_hit_obstacle(tank, obstacle)
            if intersection != None:
                #we are only applying tangential forces
                dist = math.sqrt((intersection[0] - tank.x)**2 + (intersection[1] - tank.y)**2)
                if dist < self.OBSTACLE_MAX_DISTANCE:
                    target_angle = math.atan2(intersection[1] - tank.y, intersection[0] - tank.x)
                    tangent_angle = self.normalize_angle(target_angle + math.pi/2)
                    relative_angle = self.normalize_angle(tangent_angle - tank.angle)
                    speeds.append(-1/dist)
                    angles.append(tangent_angle)
        """
        #lab2
        pos, grid = self.bzrc.get_occgrid(tank.index)
        obstacleInfluenceRange = 5
        tankWayPointIndex = self.CUR_WAYPOINT[tank.index]
        tankWayPoints = self.WAYPOINTS_ARRAY[tank.index]

        deltax = tankWayPoints[tankWayPointIndex][0] - tank.x
        deltay = tankWayPoints[tankWayPointIndex][1] - tank.y

        #for i in xrange(len(self.beliefMap)):
        #    if 1 in self.beliefMap[i]:
        #        print i, 'start', self.beliefMap[i].index(1), 'end', self.beliefMap[i][::-1].index(1)

        radius = 5
        for relativeX in xrange(50-radius, 50+radius+1):
            for relativeY in xrange(50-radius, 50+radius+1):
                SensorX = int(relativeX + pos[0] + 400)
                SensorY = int(relativeY + pos[1] + 400)
                if SensorX < 0 or SensorY < 0 or SensorX >= 800 or SensorY >= 800:
                    continue
                occupied = self.beliefMap[SensorX][SensorY]
                #print 'x', SensorX, 'y', SensorY, 'bel', occupied, 'tankx', tank.x, 'tanky', tank.y
                if occupied > .7:
                    #print 'Tangential'
                    dist = math.sqrt((relativeX - 50)**2 + (relativeY - 50)**2)
                    if dist == 0:
                        dist = 0.001
                    target_angle = math.atan2(relativeY - 50, relativeX - 50)
                    tangent_angle = self.normalize_angle(target_angle + math.pi/2)
                    relative_angle = self.normalize_angle(tangent_angle - tank.angle)
                    speed = -1/dist
                    if speed > 1:
                        speed = 1
                    speeds.append(speed)
                    angles.append(tangent_angle)

        othertanks = self.bzrc.get_othertanks()
        for enemy in othertanks:
            dist = math.sqrt((enemy.x - tank.x)**2 + (enemy.y - tank.y)**2)
            if dist < 10:
                target_angle = math.atan2(enemy.y - tank.y, enemy.x - tank.x)
                tangent_angle = self.normalize_angle(target_angle + math.pi/2)
                relative_angle = self.normalize_angle(tangent_angle - tank.angle)
                speeds.append(-1/dist)
                angles.append(tangent_angle)
        """
        if deltax != 0 and deltay != 0:
            for i in xrange(5):
                xIndex = int(tank.x+math.floor(i*(deltax / (abs(deltay) + abs(deltax)))))
                yIndex = int(tank.y+math.floor(i*(deltay / (abs(deltay) + abs(deltax)))))
                if self.beliefMap[xIndex][yIndex] > .9:
                    print 'Tangential'
                    dist = math.sqrt((xIndex - tank.x)**2 + (yIndex - tank.y)**2)
                    if dist == 0:
                        dist = 0.001
                    target_angle = math.atan2(yIndex - tank.y, xIndex - tank.x)
                    tangent_angle = self.normalize_angle(target_angle + math.pi/2)
                    relative_angle = self.normalize_angle(tangent_angle - tank.angle)
                    speeds.append(-1/dist)
                    angles.append(tangent_angle)
        """

           
        """
        if grid[tank.x+1][tank.y] > .7:
            #get around wall to the right of the tank
        elif grid[tank.x-1][tank.y] > .7:
            #get around wall to the left of the tank
        elif grid[tank.x][tank.y+1] > .7:
            #get around wall above the tank
        elif grid[tank.x][tank.y-1] > .7:
            #get around wall below the tank
        """
                
        return zip(speeds, angles)
        
    """def getSecondaryTangentialVectors(self,tank,obstacles):
        x = tank.x
        y = tank.y
        for(obstacle in obstacles:
            x1 = obstacle[0][0]
            x2 = obstacle[0][1]
            x3 = obstacle[0][2]
            x4 = obstacle[0][3]
            y1 = obstacle[0][0]
            y2 = obstacle[0][1]
            y3 = obstacle[0][2]
            y4 = obstacle[0][3]
            center_y = (y0+y1+y2+y3)/4
            center_x = (x0+x1+x2+x3)/4
            dist_x = 0
            dist_y = 0
            target_angle = 0
            if x > center_x:
                dist_x = x-center_x
            else:
                dist_x = center_x - x
            if y > center_y:
                dist_y = y - center_y
            else:
                dist_y = center_y - y
            
            dist = (dist_x**2+dist_y**2)**.5
            target_angle = math.atan2(center_y-y,center_x-x)"""
            
        
    #returns a pair of points defining a line
    def will_hit_obstacle(self, tank, obstacle):
        #first we need to make the lines to check for collissions.
        
        lines =[(array( [obstacle[0][0], obstacle[0][1] ] ), array( [obstacle[1][0], obstacle[1][1] ] )), 
                (array( [obstacle[1][0], obstacle[1][1] ] ), array( [obstacle[2][0], obstacle[2][1] ] )), 
                (array( [obstacle[2][0], obstacle[2][1] ] ), array( [obstacle[3][0], obstacle[3][1] ] )), 
                (array( [obstacle[3][0], obstacle[3][1] ] ), array( [obstacle[0][0], obstacle[0][1] ] ))]
        
        #calculate a future point along the tank's trajectory
        newTankX = float(tank.x + (self.OBSTACLE_MAX_DISTANCE * math.cos(tank.angle)))
        newTankY = float(tank.y + (self.OBSTACLE_MAX_DISTANCE * math.sin(tank.angle)))
        tankLine = [array( [tank.x, tank.y] ), array( [newTankX, newTankY] )]
        
        collisions = []
        for line in lines:
            if intersect(line[0], line[1], tankLine[0], tankLine[1]):
                collisions.append(line)
        
        closestIntersection = None
        closestDist = None
        for p1, p2 in collisions:
            intersection = seg_intersect(p1, p2, tankLine[0], tankLine[1])
            dist = math.sqrt((intersection[0] - tank.x)**2 + (intersection[0] - tank.y)**2)
            if closestDist == None or dist < closestDist:
                closestDist = dist
                closestIntersection = intersection
        
        return closestIntersection
                    

    def should_shoot(self, tank, flags, shots, obstacles):
        return True

    #returns the closest reachable gray to a given goal node
    def get_closest_reachable_gray(self, tank, goal):
        tankx = int(tank.x) + 400
        tanky = int(tank.y) + 400
        goalx = int(goal[0]) + 400
        goaly = int(goal[1]) + 400
        nodes = [[0, [tankx, tanky], []]] #will take (cost, (x, y), pathToHere)
        visitedNodes = [[tankx, tanky]] #keeps track of every coordinate we check, so there are no repeats
        black_threshold = 0.5 #anything less than .5 is considered black
        #search as long as there is a valid node to search
        while len(nodes) > 0:
            #sort path to make sure we get the lowest code option
            nodes = sorted(nodes, key=itemgetter(0))
            curNode = nodes.pop(0)
            nodex = curNode[1][0]
            nodey = curNode[1][1]
            if self.beliefMap[nodex][nodey] == 0.5:
                return curNode[2]
            elif self.beliefMap[nodex][nodey] <= black_threshold:
                #expand node - the nodes all around it (so 9 if we include the diagonals)
                for i in xrange(-1, 2):
                    for j in xrange(-1, 2):
                        if not (i == 0 and j == 0):
                            checkx = i + nodex
                            checky = j + nodey
                            checkedList = [checkx, checky]
                            #check if if the expanded node values are on the map and unvisited
                            if checkx >= 0 and checkx < 800 and checky >= 0 and checky < 800 and not checkedList in visitedNodes:
                                visitedNodes.append(checkedList)
                                if self.beliefMap[checkx][checky] <= black_threshold:
                                    #get the euclidian distance for this valid node
                                    dist = math.sqrt((checkx - goalx)**2 + (checky - goaly)**2)
                                    #new partial path
                                    checkPath = []
                                    checkPath.extend(curNode[2])
                                    checkPath.append([checkx - 400, (checky * -1) + 400])
                                    #add the node to the nodes array
                                    nodes.append([dist, [checkx, checky], checkPath])
        #end of while loop
        return None


#borrowed from http://www.cs.mun.ca/~rod/2500/notes/numpy-arrays/numpy-arrays.html
#
# line segment intersection using vectors
# see Computer Graphics by F.S. Hill
#
def perp( a ) :
    b = empty_like(a)
    b[0] = -a[1]
    b[1] = a[0]
    return b

# line segment a given by endpoints a1, a2
# line segment b given by endpoints b1, b2
# return 
def seg_intersect(a1,a2, b1,b2) :
    da = a2-a1
    db = b2-b1
    dp = a1-b1
    dap = perp(da)
    denom = dot( dap, db)
    num = dot( dap, dp )
    return (num / denom)*db + b1    
    
    
#borrowed from http://www.bryceboe.com/2006/10/23/line-segment-intersection-algorithm/
def ccw(A,B,C):
    return (C[1]-A[1])*(B[0]-A[0]) > (B[1]-A[1])*(C[0]-A[0])

def intersect(A,B,C,D):
    return ccw(A,C,D) != ccw(B,C,D) and ccw(A,B,C) != ccw(A,B,D)

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

    agent = basicAgent(bzrc)

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
                update_grid(numpy.array(zip(*agent.beliefMap)))
                #update_grid(numpy.array(agent.beliefMap))
            tickCounter = tickCounter + 1
    except KeyboardInterrupt:
        print "Exiting due to keyboard interrupt."
        bzrc.close()


if __name__ == '__main__':
    main()

# vim: et sw=4 sts=4
