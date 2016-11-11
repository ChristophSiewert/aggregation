import numpy as np
from numpy import array, sign
from scipy.optimize import brentq
import dendrite


class Crystal(object):
    def __init__(self):
        pass

    def max_radius(self):
        return 0.0

    def is_inside(self):
        return False
    

class Plate(Crystal):

    def L_from_a(self,a):
        #From Hong, 2007
        if a <= 2e-6:
            L = 2*a
        elif a < 5e-6:
            L = (2 + (2.4883 * (a*1e6)**0.474 - 2.0)/4.0 * ((a*1e6)-1.0)) * 1e-6
        else:
            L = (2.4883 * (a*1e6)**0.474) * 1e-6
        return L

    def __init__(self, D):
        super(Plate, self).__init__()
        self.D = D
        self.a = D/2.0
        self.L = self.L_from_a(self.a)
        self.V = 3.0*np.sqrt(3.0)/2.0 * self.a**2 * self.L
        self.A = (3.0*np.sqrt(3.0) * self.a**2 + 6*self.a*self.L)/4.0
        self.r = np.sqrt(3.0/4.0)*self.a
        self.centers = array([[0.0,self.r], [0.75*self.a,0.5*self.r], [0.75*self.a,-0.5*self.r], \
                              [0.0,-self.r], [-0.75*self.a,-0.5*self.r], [-0.75*self.a,0.5*self.r]])


    def max_radius(self):
        return max(self.a,self.L/2.0)


    def is_inside(self, x, y, z):
        inside = np.zeros(x.shape,dtype=bool)
        z_inside = abs(z)<=self.L/2.0
        rem_inside = inside[z_inside]
        x = x[z_inside]
        y = y[z_inside]
        rem_inside[:] = True

        for i in range(6):
            cx = self.centers[i][0]
            cy = self.centers[i][1]
            dx = x-cx
            dy = y-cy

            rem_inside &= (dx*cx+dy*cy <= 0)

        inside[z_inside] = rem_inside
        return inside


class Column(Plate):

    def a_from_L(self,L):
        if L < 100e-6:
            return 0.35*L
        else:
            return 3.48*(L*1e6)**0.5 * 1e-6

    def L_from_a(self,a):
        if a < 35e-6:
            return a/0.35
        else:
            return (a*1e6/3.48)**2 * 1e-6

    def __init__(self,D):
        D_plate_eq = self.a_from_L(D)*2.0
        super(Column, self).__init__(D_plate_eq)


class Dendrite(Plate):

    def L_from_a(self,a):
        #From Pruppacher and Klett
        L = (9.022e-3 * (a*2.0*1e2)**0.377)*1e-2
        return L

    def __init__(self,D,alpha=1.0,beta=0.35,gamma=0.001,num_iter=5000,grid_size=400,hex_grid=None):
        if hex_grid is None:
            hex_grid = dendrite.generate_dendrite(alpha,beta,gamma,num_iter=num_iter,grid_size=grid_size)
        self.ice = (hex_grid >= 1.0)
        self.grid_size = grid_size
        super(Dendrite, self).__init__(D)

        mg = hex_grid.max(1)
        r = np.arange(len(mg))[mg>1.0]
        D_width = r[-1]-r[0]+1.0
        self.grid_D = D_width/grid_size


    def xy_to_hex_grid(self,x,y):
        j = x * (self.grid_size*self.grid_D/self.D) + self.grid_size/2.0
        i = np.round(y * (self.grid_size*self.grid_D/self.D) + self.grid_size/2.0)
        j[np.round(j)%2==1] += 0.5
        j = np.round(j)
        return (i.astype(int),j.astype(int))


    def is_inside(self,x,y,z):
        inside = np.zeros(x.shape,dtype=bool)
        z_inside = abs(z)<=self.L/2.0
        rem_inside = inside[z_inside]
        x = x[z_inside]
        y = y[z_inside]

        (i,j) = self.xy_to_hex_grid(x,y)        
        safe = ((i>=0) & (i<self.grid_size)) & ((j>=0) & (j<self.grid_size))

        rem_inside[safe] = self.ice[i[safe],j[safe]]

        inside[z_inside] = rem_inside
        return inside


#6-branch bullet rosette
class Rosette(Crystal):
    def __init__(self, D):
        super(Rosette, self).__init__()
        
        #From Hong, 2007
        alpha = 28*(np.pi/180.0)
        f = np.sqrt(3)*1.552/np.tan(alpha)        
        def L_func(L):
            return 2*L + f*L**0.63 - D*1e6
        #solve L from D numerically
        self.L = brentq(L_func, 0, D*1e6/2.0) * 1e-6        
        self.a = (1.552 * (self.L*1e6)**0.63) * 1e-6
        self.t = np.sqrt(3)*self.a/(2*np.tan(alpha))
        self.D = D
        
    def max_radius(self):
        return self.D/2.0
    
    def _inside_bullet(self,x,y,z):
        inside = (abs(z) < self.D/2.0)
        z_ratio = abs(z)/self.t
        z_ratio[z_ratio>1] = 1.0 
        a = self.a * z_ratio
        r = np.sqrt(3.0/4.0)*a
        inside &= (abs(y) <= r)        
        for (sx, sy) in [[1,1], [-1,1], [1,-1], [-1,-1]]:
            cx = sx * 0.75*a 
            cy = sy * 0.5*r
            inside &= ((x-cx)*cx+(y-cy)*cy < 0)
        return inside
        
    def is_inside(self,x,y,z):
        inside = np.zeros(x.shape, dtype=bool)
        inside |= self._inside_bullet(x,y,z)
        inside |= self._inside_bullet(y,z,x)
        inside |= self._inside_bullet(z,x,y)
        return inside
    
    
class Bullet(Crystal):
    def __init__(self, D):
        super(Bullet, self).__init__()
        
        #From Hong, 2007
        alpha = 28*(np.pi/180.0)
        f = np.sqrt(3)*1.552/np.tan(alpha)        
        def L_func(L):
            return 2*L + f*L**0.63 - D*1e6
        #solve L from D numerically
        self.L = brentq(L_func, 0, D*1e6/2.0) * 1e-6        
        self.a = (1.552 * (self.L*1e6)**0.63) * 1e-6
        self.t = np.sqrt(3)*self.a/(2*np.tan(alpha))
        self.D = D
        
    def max_radius(self):
        return self.D/2.0
    
    def _inside_bullet(self,x,y,z):
        inside = (z > 0) & (abs(z) < self.D/2.0)
        z_ratio = abs(z)/self.t
        z_ratio[z_ratio>1] = 1.0 
        a = self.a * z_ratio
        r = np.sqrt(3.0/4.0)*a
        inside &= (abs(y) <= r)        
        for (sx, sy) in [[1,1], [-1,1], [1,-1], [-1,-1]]:
            cx = sx * 0.75*a 
            cy = sy * 0.5*r
            inside &= ((x-cx)*cx+(y-cy)*cy < 0)
        return inside
        
    def is_inside(self,x,y,z):
        inside = np.zeros(x.shape, dtype=bool)
        inside |= self._inside_bullet(x,y,z)  
        return inside
    
    
class Spheroid(Crystal):
    def __init__(self, D_max, axis_ratio=1.0):
        super(Spheroid, self).__init__()
        self.a = D_max/2.0
        self.c = self.a * axis_ratio
        self.axis_ratio = axis_ratio
        
    def max_radius(self): 
        return self.a
    
    def is_inside(self,x,y,z):
        return (x**2+y**2)/(self.a**2) + (z/self.c)**2 <= 1
    
    
class Needle(Column):
    #From Pruppacher and Klett
    def L_from_a(self, a):  
        return (1.0/3.527e-2 * 2*a*(1e2))**(1.0/0.437) * 1e-2
    
    def a_from_L(self, L):
        return 3.527e-2 * (L*1e2)**0.437 / 2.0 * 1e-2 

