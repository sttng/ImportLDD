bl_info = {
    "name": "Import LEGO Digital Designer",
    "description": "Import LEGO Digital Designer scenes in .lxf and .lxfml formats",
    "author": "123 <123@gmail.com>",
    "version": (0, 0, 1),
    "blender": (2, 90, 0),
    "location": "File > Import",
    "warning": "Alpha",
    "wiki_url": "https://github.com/",
    "tracker_url": "https://github.com/",
    "category": "Import-Export"
    }

import bpy
import mathutils
from bpy_extras.io_utils import (
        ImportHelper,
        orientation_helper,
        axis_conversion,
        )








#!/usr/bin/env python
# pylddlib version 0.4.9.7
# based on pyldd2obj version 0.4.8 - Copyright (c) 2019 by jonnysp
#
# Updates:
# 0.4.9.7 corrected bug of incorrectly parsing the primitive xml file, specifically with comments. Add support LDDLIFTREE envirnment variable to set location of db.lif.
# 0.4.9.6 preliminary Linux support
# 0.4.9.5 corrected bug of incorrectly Bounding / GeometryBounding parsing the primitive xml file.
# 0.4.9.4 improved lif.db checking for crucial files (because of the infamous botched 4.3.12 LDD Windows update).
# 0.4.9.3 improved Windows and Python 3 compatibility
# 0.4.9.2 changed handling of material = 0 for a part. Now a 0 will choose the 1st material (the base material of a part) and not the previous material of the subpart before. This will fix "Chicken Helmet Part 11262". It may break other parts and this change needs further regression.
# 0.4.9.1 improved custom2DField handling, fixed decorations bug, improved material assignments handling
# 0.4.9 updates to support reading extracted db.lif from db folder
#
# License: MIT License
#

import os
import platform
import sys
import math
import struct
import zipfile
from xml.dom import minidom
import uuid
import random
import time

if sys.version_info < (3, 0):
    reload(sys)
    sys.setdefaultencoding('utf-8')

PRIMITIVEPATH = '/Primitives/'
GEOMETRIEPATH = PRIMITIVEPATH + 'LOD0/'
DECORATIONPATH = '/Decorations/'
MATERIALNAMESPATH = '/MaterialNames/'

LOGOONSTUDSCONNTYPE = {"0:4", "0:4:1", "0:4:2", "0:4:33", "2:4:1", "2:4:34"}

class Matrix3D:
    def __init__(self, n11=1,n12=0,n13=0,n14=0,n21=0,n22=1,n23=0,n24=0,n31=0,n32=0,n33=1,n34=0,n41=0,n42=0,n43=0,n44=1):
        self.n11 = n11
        self.n12 = n12
        self.n13 = n13
        self.n14 = n14
        self.n21 = n21
        self.n22 = n22
        self.n23 = n23
        self.n24 = n24
        self.n31 = n31
        self.n32 = n32
        self.n33 = n33
        self.n34 = n34
        self.n41 = n41
        self.n42 = n42
        self.n43 = n43
        self.n44 = n44

    def __str__(self):
        return '[{0},{1},{2},{3},{4},{5},{6},{7},{8},{9},{10},{11},{12},{13},{14},{15}]'.format(self.n11, self.n12, self.n13,self.n14,self.n21, self.n22, self.n23,self.n24,self.n31, self.n32, self.n33,self.n34,self.n41, self.n42, self.n43,self.n44)

    def rotate(self,angle=0,axis=0):
        c = math.cos(angle)
        s = math.sin(angle)
        t = 1 - c

        tx = t * axis.x
        ty = t * axis.y
        tz = t * axis.z

        sx = s * axis.x
        sy = s * axis.y
        sz = s * axis.z

        self.n11 = c + axis.x * tx
        self.n12 = axis.y * tx + sz
        self.n13 = axis.z * tx - sy
        self.n14 = 0

        self.n21 = axis.x * ty - sz
        self.n22 = c + axis.y * ty
        self.n23 = axis.z * ty + sx
        self.n24 = 0

        self.n31 = axis.x * tz + sy
        self.n32 = axis.y * tz - sx
        self.n33 = c + axis.z * tz
        self.n34 = 0

        self.n41 = 0
        self.n42 = 0
        self.n43 = 0
        self.n44 = 1

    def __mul__(self, other): 
        return Matrix3D(
            self.n11 * other.n11 + self.n21 * other.n12 + self.n31 * other.n13 + self.n41 * other.n14,
            self.n12 * other.n11 + self.n22 * other.n12 + self.n32 * other.n13 + self.n42 * other.n14,
            self.n13 * other.n11 + self.n23 * other.n12 + self.n33 * other.n13 + self.n43 * other.n14,
            self.n14 * other.n11 + self.n24 * other.n12 + self.n34 * other.n13 + self.n44 * other.n14,
            self.n11 * other.n21 + self.n21 * other.n22 + self.n31 * other.n23 + self.n41 * other.n24,
            self.n12 * other.n21 + self.n22 * other.n22 + self.n32 * other.n23 + self.n42 * other.n24,
            self.n13 * other.n21 + self.n23 * other.n22 + self.n33 * other.n23 + self.n43 * other.n24,
            self.n14 * other.n21 + self.n24 * other.n22 + self.n34 * other.n23 + self.n44 * other.n24,
            self.n11 * other.n31 + self.n21 * other.n32 + self.n31 * other.n33 + self.n41 * other.n34,
            self.n12 * other.n31 + self.n22 * other.n32 + self.n32 * other.n33 + self.n42 * other.n34,
            self.n13 * other.n31 + self.n23 * other.n32 + self.n33 * other.n33 + self.n43 * other.n34,
            self.n14 * other.n31 + self.n24 * other.n32 + self.n34 * other.n33 + self.n44 * other.n34,
            self.n11 * other.n41 + self.n21 * other.n42 + self.n31 * other.n43 + self.n41 * other.n44,
            self.n12 * other.n41 + self.n22 * other.n42 + self.n32 * other.n43 + self.n42 * other.n44,
            self.n13 * other.n41 + self.n23 * other.n42 + self.n33 * other.n43 + self.n43 * other.n44,
            self.n14 * other.n41 + self.n24 * other.n42 + self.n34 * other.n43 + self.n44 * other.n44
            )

class Point3D:
    def __init__(self, x=0,y=0,z=0):
        self.x = x
        self.y = y
        self.z = z

    def __str__(self):
        return '[{0},{1},{2}]'.format(self.x, self.y,self.z)

    def string(self,prefix = "v"):
        return '{0} {1:f} {2:f} {3:f}\n'.format(prefix ,self.x , self.y, self.z)

    def transformW(self,matrix):
        x = matrix.n11 * self.x + matrix.n21 * self.y + matrix.n31 * self.z
        y = matrix.n12 * self.x + matrix.n22 * self.y + matrix.n32 * self.z
        z = matrix.n13 * self.x + matrix.n23 * self.y + matrix.n33 * self.z
        self.x = x
        self.y = y
        self.z = z

    def transform(self,matrix):
        x = matrix.n11 * self.x + matrix.n21 * self.y + matrix.n31 * self.z + matrix.n41
        y = matrix.n12 * self.x + matrix.n22 * self.y + matrix.n32 * self.z + matrix.n42
        z = matrix.n13 * self.x + matrix.n23 * self.y + matrix.n33 * self.z + matrix.n43
        self.x = x
        self.y = y
        self.z = z

    def copy(self):
        return Point3D(x=self.x,y=self.y,z=self.z)

class Point2D:
    def __init__(self, x=0,y=0):
        self.x = x
        self.y = y
    def __str__(self):
        return '[{0},{1}]'.format(self.x, self.y * -1)
    def string(self,prefix="t"):
        return '{0} {1:f} {2:f}\n'.format(prefix , self.x, self.y * -1 )
    def copy(self):
        return Point2D(x=self.x,y=self.y)

class Face:
    def __init__(self,a=0,b=0,c=0):
        self.a = a
        self.b = b
        self.c = c
    def string(self,prefix="f", indexOffset=0 ,textureoffset=0):
        if textureoffset == 0:
            return prefix + ' {0}//{0} {1}//{1} {2}//{2}\n'.format(self.a + indexOffset, self.b + indexOffset, self.c + indexOffset)
        else:
            return prefix + ' {0}/{3}/{0} {1}/{4}/{1} {2}/{5}/{2}\n'.format(self.a + indexOffset, self.b + indexOffset, self.c + indexOffset,self.a + textureoffset, self.b + textureoffset, self.c + textureoffset)
    def __str__(self):
        return '[{0},{1},{2}]'.format(self.a, self.b, self.c)

class Group:
    def __init__(self, node):
        self.partRefs = node.getAttribute('partRefs').split(',')
        
class Bone:
    def __init__(self, node):
        self.refID = node.getAttribute('refID')
        (a, b, c, d, e, f, g, h, i, x, y, z) = map(float, node.getAttribute('transformation').split(','))
        self.matrix = Matrix3D(n11=a,n12=b,n13=c,n14=0,n21=d,n22=e,n23=f,n24=0,n31=g,n32=h,n33=i,n34=0,n41=x,n42=y,n43=z,n44=1)

class Part:
    def __init__(self, node):
        self.isGrouped = False
        self.GroupIDX = 0
        self.Bones = []
        self.refID = node.getAttribute('refID')
        self.designID = node.getAttribute('designID')
        self.materials = list(map(str, node.getAttribute('materials').split(',')))
        
        lastm = '0'
        for i, m in enumerate(self.materials):
            if (m == '0'):
                # self.materials[i] = lastm
                self.materials[i] = self.materials[0] #in case of 0 choose the 'base' material
            else:
                lastm = m
        if node.hasAttribute('decoration'):
            self.decoration = list(map(str,node.getAttribute('decoration').split(',')))
        for childnode in node.childNodes:
            if childnode.nodeName == 'Bone':
                self.Bones.append(Bone(node=childnode)) 

class Brick:
    def __init__(self, node):
        self.refID = node.getAttribute('refID')
        self.designID = node.getAttribute('designID')
        self.Parts = []
        for childnode in node.childNodes:
            if childnode.nodeName == 'Part':
                self.Parts.append(Part(node=childnode))

class SceneCamera:
    def __init__(self, node):
        self.refID = node.getAttribute('refID')
        (a, b, c, d, e, f, g, h, i, x, y, z) = map(float, node.getAttribute('transformation').split(','))
        self.matrix = Matrix3D(n11=a,n12=b,n13=c,n14=0,n21=d,n22=e,n23=f,n24=0,n31=g,n32=h,n33=i,n34=0,n41=x,n42=y,n43=z,n44=1)
        self.fieldOfView = float(node.getAttribute('fieldOfView'))
        self.distance = float(node.getAttribute('distance'))

class Scene:
    def __init__(self, file):
        self.Bricks = []
        self.Scenecamera = []
        self.Groups = []

        if file.endswith('.lxfml'):
            with open(file, "rb") as file:
                data = file.read()
        elif file.endswith('.lxf'):
            zf = zipfile.ZipFile(file, 'r')
            data = zf.read('IMAGE100.LXFML')
        else:
            return

        xml = minidom.parseString(data)
        self.Name = xml.firstChild.getAttribute('name')
                
        for node in xml.firstChild.childNodes: 
            if node.nodeName == 'Meta':
                for childnode in node.childNodes:
                    if childnode.nodeName == 'BrickSet':
                        self.Version = str(childnode.getAttribute('version'))
            elif node.nodeName == 'Cameras':
                for childnode in node.childNodes:
                    if childnode.nodeName == 'Camera':
                        self.Scenecamera.append(SceneCamera(node=childnode))
            elif node.nodeName == 'Bricks':
                for childnode in node.childNodes:
                    if childnode.nodeName == 'Brick':
                        self.Bricks.append(Brick(node=childnode))
            elif node.nodeName == 'GroupSystems':
                for childnode in node.childNodes:
                    if childnode.nodeName == 'GroupSystem':
                        for childnode in childnode.childNodes:
                            if childnode.nodeName == 'Group':
                                self.Groups.append(Group(node=childnode))

        for i in range(len(self.Groups)):
            for brick in self.Bricks:
                for part in brick.Parts:
                    if part.refID in self.Groups[i].partRefs:
                        part.isGrouped = True
                        part.GroupIDX = i

        print('Scene "'+ self.Name + '" Brickversion: ' + str(self.Version))

class GeometryReader:
    def __init__(self, data):
        self.offset = 0
        self.data = data
        self.positions = []
        self.normals = []
        self.textures = []
        self.faces = []
        self.bonemap = {}
        self.texCount = 0
        self.outpositions = []
        self.outnormals = []

        if self.readInt() == 1111961649:
            self.valueCount = self.readInt()
            self.indexCount = self.readInt()
            self.faceCount = int(self.indexCount / 3)
            options = self.readInt()

            for i in range(0, self.valueCount):
                self.positions.append(Point3D(x=self.readFloat(),y= self.readFloat(),z=self.readFloat()))

            for i in range(0, self.valueCount):
                 self.normals.append(Point3D(x=self.readFloat(),y= self.readFloat(),z=self.readFloat()))

            if (options & 3) == 3:
                self.texCount = self.valueCount
                for i in range(0, self.valueCount):
                    self.textures.append(Point2D(x=self.readFloat(), y=self.readFloat()))

            for i in range(0, self.faceCount):
                self.faces.append(Face(a=self.readInt(),b=self.readInt(),c=self.readInt()))

            if (options & 48) == 48:
                num = self.readInt()
                self.offset += (num * 4) + (self.indexCount * 4)
                num = self.readInt()
                self.offset += (3 * num * 4) + (self.indexCount * 4)

            bonelength = self.readInt()
            self.bonemap = [0] * self.valueCount

            if (bonelength > self.valueCount) or (bonelength > self.faceCount):
                datastart = self.offset
                self.offset += bonelength
                for i in range(0, self.valueCount):
                    boneoffset = self.readInt() + 4
                    self.bonemap[i] = self.read_Int(datastart + boneoffset)
    
    def read_Int(self,_offset):
        if sys.version_info < (3, 0):
            return int(struct.unpack_from('i', self.data, _offset)[0])
        else:
            return int.from_bytes(self.data[_offset:_offset + 4], byteorder='little')

    def readInt(self):
        if sys.version_info < (3, 0):
            ret = int(struct.unpack_from('i', self.data, self.offset)[0])
        else:
            ret = int.from_bytes(self.data[self.offset:self.offset + 4], byteorder='little')
        self.offset += 4
        return ret

    def readFloat(self):
        ret = float(struct.unpack_from('f', self.data, self.offset)[0])
        self.offset += 4
        return ret

class Geometry:
    def __init__(self, designID, database):
        self.designID = designID
        self.Parts = {} 
        self.maxGeoBounding = -1	
        self.studsFields2D = []
        
        GeometryLocation = os.path.normpath('{0}{1}{2}'.format(GEOMETRIEPATH, designID,'.g'))
        GeometryCount = 0
        while str(GeometryLocation) in database.filelist:
            self.Parts[GeometryCount] = GeometryReader(data=database.filelist[GeometryLocation].read())
            GeometryCount += 1
            GeometryLocation = os.path.normpath('{0}{1}{2}{3}'.format(GEOMETRIEPATH, designID,'.g',GeometryCount))

        primitive = Primitive(data = database.filelist[os.path.normpath(PRIMITIVEPATH + designID + '.xml')].read())
        self.Partname = primitive.Designname
        self.studsFields2D = primitive.Fields2D
        try:
            geoBoundingList = [abs(float(primitive.Bounding['minX']) - float(primitive.Bounding['maxX'])), abs(float(primitive.Bounding['minY']) - float(primitive.Bounding['maxY'])), abs(float(primitive.Bounding['minZ']) - float(primitive.Bounding['maxZ']))]
            geoBoundingList.sort() 
            self.maxGeoBounding = geoBoundingList[-1]
        except KeyError as e:
            print('\nBounding errror in part {0}: {1}\n'.format(designID, e))
                    
        # preflex
        for part in self.Parts:
            # transform
            for i, b in enumerate(primitive.Bones):
                # positions
                for j, p in enumerate(self.Parts[part].positions):
                    if (self.Parts[part].bonemap[j] == i):
                        self.Parts[part].positions[j].transform(b.matrix)
                # normals
                for k, n in enumerate(self.Parts[part].normals):
                    if (self.Parts[part].bonemap[k] == i):
                        self.Parts[part].normals[k].transformW(b.matrix)

    def valuecount(self):
        count = 0
        for part in self.Parts:
            count += self.Parts[part].valueCount
        return count

    def facecount(self):
        count = 0
        for part in self.Parts:
            count += self.Parts[part].faceCount
        return count

    def texcount(self):
        count = 0
        for part in self.Parts:
            count += self.Parts[part].texCount
        return count

class Bone2:
    def __init__(self,boneId=0, angle=0, ax=0, ay=0, az=0, tx=0, ty=0, tz=0):
        self.boneId = boneId
        rotationMatrix = Matrix3D()
        rotationMatrix.rotate(angle = -angle * math.pi / 180.0,axis = Point3D(x=ax,y=ay,z=az))
        p = Point3D(x=tx,y=ty,z=tz)
        p.transformW(rotationMatrix)
        rotationMatrix.n41 -= p.x
        rotationMatrix.n42 -= p.y
        rotationMatrix.n43 -= p.z
        self.matrix = rotationMatrix

class Field2D:
    def __init__(self, type=0, width=0, height=0, angle=0, ax=0, ay=0, az=0, tx=0, ty=0, tz=0, field2DRawData='none'):
        self.type = type
        self.field2DRawData = field2DRawData
        rotationMatrix = Matrix3D()
        rotationMatrix.rotate(angle = -angle * math.pi / 180.0, axis = Point3D(x=ax,y=ay,z=az))
        p = Point3D(x=tx,y=ty,z=tz)
        p.transformW(rotationMatrix)
        rotationMatrix.n41 -= p.x
        rotationMatrix.n42 -= p.y
        rotationMatrix.n43 -= p.z
        
        self.matrix = rotationMatrix
        self.custom2DField = []
        
        #The height and width are always double the number of studs. The contained text is a 2D array that is always height + 1 and width + 1.
        rows_count = height + 1
        cols_count = width + 1
        # creation looks reverse
        # create an array of "cols_count" cols, for each of the "rows_count" rows
        # all elements are initialized to 0
        self.custom2DField = [[0 for j in range(cols_count)] for i in range(rows_count)]
        custom2DFieldString = field2DRawData.replace('\r', '').replace('\n', '').replace(' ', '')
        custom2DFieldArr = custom2DFieldString.strip().split(',')
        
        k = 0
        for i in range(rows_count):
            for j in range(cols_count):
                self.custom2DField[i][j] = custom2DFieldArr[k]
                k += 1
        
    def __str__(self):
        return '[type="{0}" transform="{1}" custom2DField="{2}"]'.format(self.type, self.matrix, self.custom2DField)

class CollisionBox:
    def __init__(self, sX=0, sY=0, sZ=0, angle=0, ax=0, ay=0, az=0, tx=0, ty=0, tz=0):
        rotationMatrix = Matrix3D()
        rotationMatrix.rotate(angle = -angle * math.pi / 180.0, axis = Point3D(x=ax,y=ay,z=az))
        p = Point3D(x=tx,y=ty,z=tz)
        p.transformW(rotationMatrix)
        rotationMatrix.n41 -= p.x
        rotationMatrix.n42 -= p.y
        rotationMatrix.n43 -= p.z
        
        self.matrix = rotationMatrix
        self.corner = Point3D(x=sX,y=sY,z=sZ)
        self.positions = []
        
        self.positions.append(Point3D(x=0, y=0, z=0))
        self.positions.append(Point3D(x=sX, y=0, z=0))
        self.positions.append(Point3D(x=0, y=sY, z=0))
        self.positions.append(Point3D(x=sX, y=sY, z=0))
        self.positions.append(Point3D(x=0, y=0, z=sZ))
        self.positions.append(Point3D(x=0, y=sY, z=sZ))
        self.positions.append(Point3D(x=sX ,y=0, z=sZ))
        self.positions.append(Point3D(x=sX ,y=sY, z=sZ))
    
    def __str__(self):
        return '[0,0,0] [{0},0,0] [0,{1},0] [{0},{1},0] [0,0,{2}] [0,{1},{2}] [{0},0,{2}] [{0},{1},{2}]'.format(self.corner.x, self.corner.y, self.corner.z)

class Primitive:
    def __init__(self, data):
        self.Designname = ''
        self.Bones = []
        self.Fields2D = []
        self.CollisionBoxes = []
        self.PhysicsAttributes = {}
        self.Bounding = {}
        self.GeometryBounding = {}
        xml = minidom.parseString(data)
        root = xml.documentElement
        for node in root.childNodes:
            if node.__class__.__name__.lower() == 'comment':
                self.comment = node[0].nodeValue
            if node.nodeName == 'Flex': 
                for node in node.childNodes:
                    if node.nodeName == 'Bone':
                        self.Bones.append(Bone2(boneId=int(node.getAttribute('boneId')), angle=float(node.getAttribute('angle')), ax=float(node.getAttribute('ax')), ay=float(node.getAttribute('ay')), az=float(node.getAttribute('az')), tx=float(node.getAttribute('tx')), ty=float(node.getAttribute('ty')), tz=float(node.getAttribute('tz'))))
            elif node.nodeName == 'Annotations':
                for childnode in node.childNodes:
                    if childnode.nodeName == 'Annotation' and childnode.hasAttribute('designname'):
                        self.Designname = childnode.getAttribute('designname')
            elif node.nodeName == 'Collision':
                for childnode in node.childNodes:
                    if childnode.nodeName == 'Box':
                        self.CollisionBoxes.append(CollisionBox(sX=float(childnode.getAttribute('sX')), sY=float(childnode.getAttribute('sY')), sZ=float(childnode.getAttribute('sZ')), angle=float(childnode.getAttribute('angle')), ax=float(childnode.getAttribute('ax')), ay=float(childnode.getAttribute('ay')), az=float(childnode.getAttribute('az')), tx=float(childnode.getAttribute('tx')), ty=float(childnode.getAttribute('ty')), tz=float(childnode.getAttribute('tz'))))
            elif node.nodeName == 'PhysicsAttributes':
                self.PhysicsAttributes = {"inertiaTensor": node.getAttribute('inertiaTensor'),"centerOfMass": node.getAttribute('centerOfMass'),"mass": node.getAttribute('mass'),"frictionType": node.getAttribute('frictionType')}
            elif node.nodeName == 'Bounding':
                for childnode in node.childNodes:
                    if childnode.nodeName == 'AABB':
                        self.Bounding = {"minX": childnode.getAttribute('minX'), "minY": childnode.getAttribute('minY'), "minZ": childnode.getAttribute('minZ'), "maxX": childnode.getAttribute('maxX'), "maxY": childnode.getAttribute('maxY'), "maxZ": childnode.getAttribute('maxZ')}
            elif node.nodeName == 'GeometryBounding':
                for childnode in node.childNodes:
                    if childnode.nodeName == 'AABB':
                        self.GeometryBounding = {"minX": childnode.getAttribute('minX'), "minY": childnode.getAttribute('minY'), "minZ": childnode.getAttribute('minZ'), "maxX": childnode.getAttribute('maxX'), "maxY": childnode.getAttribute('maxY'), "maxZ": childnode.getAttribute('maxZ')}
            elif node.nodeName == 'Connectivity':
                for childnode in node.childNodes:
                    if childnode.nodeName == 'Custom2DField':
                        self.Fields2D.append(Field2D(type=int(childnode.getAttribute('type')), width=int(childnode.getAttribute('width')), height=int(childnode.getAttribute('height')), angle=float(childnode.getAttribute('angle')), ax=float(childnode.getAttribute('ax')), ay=float(childnode.getAttribute('ay')), az=float(childnode.getAttribute('az')), tx=float(childnode.getAttribute('tx')), ty=float(childnode.getAttribute('ty')), tz=float(childnode.getAttribute('tz')), field2DRawData=str(childnode.firstChild.data)))
            elif node.nodeName == 'Decoration':
                self.Decoration = {"faces": node.getAttribute('faces'), "subMaterialRedirectLookupTable": node.getAttribute('subMaterialRedirectLookupTable')}

class LOCReader:
    def __init__(self, data):
        self.offset = 0
        self.values = {}
        self.data = data
        if sys.version_info < (3, 0):
            if ord(self.data[0]) == 50 and ord(self.data[1]) == 0:
                self.offset += 2
                while self.offset < len(self.data):
                    key = self.NextString().replace('Material', '')
                    value = self.NextString()
                    self.values[key] = value
        else:
            if int(self.data[0]) == 50 and int(self.data[1]) == 0:
                self.offset += 2
                while self.offset < len(self.data):
                    key = self.NextString().replace('Material', '')
                    value = self.NextString()
                    self.values[key] = value

    def NextString(self):
        out = ''
        if sys.version_info < (3, 0):
            t = ord(self.data[self.offset])
            self.offset += 1
            while not t == 0:
                out = '{0}{1}'.format(out,chr(t))
                t = ord(self.data[self.offset])
                self.offset += 1
        else:
            t = int(self.data[self.offset])
            self.offset += 1
            while not t == 0:
                out = '{0}{1}'.format(out,chr(t))
                t = int(self.data[self.offset])
                self.offset += 1
        return out

class Materials:
    def __init__(self, data):
        self.Materials = {}
        xml = minidom.parseString(data)
        for node in xml.firstChild.childNodes: 
            if node.nodeName == 'Material':
                self.Materials[node.getAttribute('MatID')] = Material(node.getAttribute('MatID'),r=int(node.getAttribute('Red')), g=int(node.getAttribute('Green')), b=int(node.getAttribute('Blue')), a=int(node.getAttribute('Alpha')), mtype=str(node.getAttribute('MaterialType')))

    def setLOC(self, loc):
        for key in loc.values:
            if key in self.Materials:
                self.Materials[key].name = loc.values[key].replace(" ", "_")

    def getMaterialbyId(self, mid):
        return self.Materials[mid]

class Material:
    def __init__(self,id, r, g, b, a, mtype):
        self.id = id
        self.name = ''
        self.mattype = mtype
        self.r = float(r)
        self.g = float(g)
        self.b = float(b)
        self.a = float(a)
    def string(self):
        out = 'Kd {0} {1} {2}\nKa 1.600000 1.600000 1.600000\nKs 0.400000 0.400000 0.400000\nNs 3.482202\nTf 1 1 1\n'.format( self.r / 255, self.g / 255,self.b / 255) 
        if self.a < 255:
            out += 'Ni 1.575\n' + 'd {0}'.format(0.05) + '\n' + 'Tr {0}\n'.format(0.05)
        return out

class DBinfo:
    def __init__(self, data):
        xml = minidom.parseString(data)
        self.Version = xml.getElementsByTagName('Bricks')[0].attributes['version'].value
        print('DB Version: ' + str(self.Version))

class DBFolderFile:
    def __init__(self, name, handle):
        self.handle = handle
        self.name = name

    def read(self):
        reader = open(self.handle, "rb")
        try:
            filecontent = reader.read()
            reader.close()
            return filecontent
        finally:
            reader.close()
        
class LIFFile:
    def __init__(self, name, offset, size, handle):
        self.handle = handle
        self.name = name
        self.offset = offset
        self.size = size

    def read(self):
        self.handle.seek(self.offset, 0)
        return self.handle.read(self.size)

class DBFolderReader:
    def __init__(self, folder):
        self.filelist = {}
        self.initok = False
        self.location = folder
        self.dbinfo = None
        
        try:
            os.path.isdir(self.location)
        except Exception as e:
            self.initok = False
            print("db folder read FAIL")
            return
        else:
            self.parse()
            if self.fileexist(os.path.join(self.location,'Materials.xml')) and self.fileexist(os.path.join(self.location, 'info.xml')) and self.fileexist(os.path.normpath(os.path.join(self.location, MATERIALNAMESPATH, 'EN/localizedStrings.loc'))):
                self.dbinfo = DBinfo(data=self.filelist[os.path.join(self.location,'info.xml')].read())
                print("DB folder OK.")
                self.initok = True
            else:
                print("DB folder ERROR")
                
    def fileexist(self, filename):
        return filename in self.filelist

    def parse(self):
        for path, subdirs, files in os.walk(self.location):
            for name in files:
                entryName = os.path.join(path, name)
                self.filelist[entryName] = DBFolderFile(name=entryName, handle=entryName)
    
class LIFReader:
    def __init__(self, file):
        self.packedFilesOffset = 84
        self.filelist = {}
        self.initok = False
        self.location = file
        self.dbinfo = None

        try:
            self.filehandle = open(self.location, "rb")
            self.filehandle.seek(0, 0)
        except Exception as e:
            self.initok = False
            print("Database FAIL")
            return
        else:
            if self.filehandle.read(4).decode() == "LIFF":
                self.parse(prefix='', offset=self.readInt(offset=72) + 64)
                if self.fileexist(os.path.normpath('/Materials.xml')) and self.fileexist(os.path.normpath('/info.xml')) and self.fileexist(os.path.normpath(MATERIALNAMESPATH + 'EN/localizedStrings.loc')):
                    self.dbinfo = DBinfo(data=self.filelist[os.path.normpath('/info.xml')].read())
                    print("Database OK.")
                    self.initok = True
                else:
                    print("Database ERROR")
            else:
                print("Database FAIL")
                self.initok = False

    def fileexist(self,filename):
        return filename in self.filelist

    def parse(self, prefix='', offset=0):
        if prefix == '':
            offset += 36
        else:
            offset += 4

        count = self.readInt(offset=offset)

        for i in range(0, count):
            offset += 4
            entryType = self.readShort(offset=offset)
            offset += 6

            entryName = '{0}{1}'.format(prefix,'/');
            self.filehandle.seek(offset + 1, 0)
            if sys.version_info < (3, 0):
                t = ord(self.filehandle.read(1))
            else:
                t = int.from_bytes(self.filehandle.read(1), byteorder='big')

            while not t == 0:
                entryName ='{0}{1}'.format(entryName,chr(t))
                self.filehandle.seek(1, 1)
                if sys.version_info < (3, 0):
                    t = ord(self.filehandle.read(1))
                else:
                    t = int.from_bytes(self.filehandle.read(1), byteorder='big')

                offset += 2

            offset += 6
            self.packedFilesOffset += 20

            if entryType == 1:
                offset = self.parse(prefix=entryName, offset=offset)
            elif entryType == 2:
                fileSize = self.readInt(offset=offset) - 20
                self.filelist[os.path.normpath(entryName)] = LIFFile(name=entryName, offset=self.packedFilesOffset, size=fileSize, handle=self.filehandle)
                offset += 24
                self.packedFilesOffset += fileSize

        return offset

    def readInt(self, offset=0):
        self.filehandle.seek(offset, 0)
        if sys.version_info < (3, 0):
            return int(struct.unpack('>i', self.filehandle.read(4))[0])
        else:
            return int.from_bytes(self.filehandle.read(4), byteorder='big')

    def readShort(self, offset=0):
        self.filehandle.seek(offset, 0)
        if sys.version_info < (3, 0):
            return int(struct.unpack('>h', self.filehandle.read(2))[0])
        else:
            return int.from_bytes(self.filehandle.read(2), byteorder='big')

class Converter:
    def LoadDBFolder(self, dbfolderlocation):
        self.database = DBFolderReader(folder=dbfolderlocation)

        if self.database.initok and self.database.fileexist(os.path.join(dbfolderlocation,'Materials.xml')) and self.database.fileexist(MATERIALNAMESPATH + 'EN/localizedStrings.loc'):
            self.allMaterials = Materials(data=self.database.filelist[os.path.join(dbfolderlocation,'Materials.xml')].read());
            self.allMaterials.setLOC(loc=LOCReader(data=self.database.filelist[MATERIALNAMESPATH + 'EN/localizedStrings.loc'].read()))
    
    def LoadDatabase(self,databaselocation):
        self.database = LIFReader(file=databaselocation)

        if self.database.initok and self.database.fileexist('/Materials.xml') and self.database.fileexist(MATERIALNAMESPATH + 'EN/localizedStrings.loc'):
            self.allMaterials = Materials(data=self.database.filelist['/Materials.xml'].read());
            self.allMaterials.setLOC(loc=LOCReader(data=self.database.filelist[MATERIALNAMESPATH + 'EN/localizedStrings.loc'].read()))

    def LoadScene(self,filename):
        if self.database.initok:
            self.scene = Scene(file=filename)

    def Export(self,filename):
        invert = Matrix3D() 
        #invert.n33 = -1 #uncomment to invert the Z-Axis
        
        indexOffset = 1
        textOffset = 1
        usedmaterials = []
        geometriecache = {}
        writtenribs = []
        #usedgeo = [] not used currently
        
        start_time = time.time()
        
        
        total = len(self.scene.Bricks)
        current = 0
        currentpart = 0
        
        # miny used for floor plane later
        miny = 1000
        
        #useplane = cl.useplane
        #usenormal = cl.usenormal
        #uselogoonstuds = cl.uselogoonstuds
        #fstop = cl.args.fstop
        #fov =  cl.args.fov
        
        global_matrix = axis_conversion(from_forward='-Z', from_up='Y', to_forward='Y',to_up='Z').to_4x4()
        #col = bpy.data.collections.get("Collection")
        col = bpy.data.collections.new(self.scene.Name)
        bpy.context.scene.collection.children.link(col)
        
        for cam in self.scene.Scenecamera:
            camera_data = bpy.data.cameras.new(name='Cam_{0}'.format(cam.refID))   
            camera_object = bpy.data.objects.new('Cam_{0}'.format(cam.refID), camera_data)
            transform_matrix = mathutils.Matrix(((cam.matrix.n11, cam.matrix.n21, cam.matrix.n31, cam.matrix.n41),(cam.matrix.n12, cam.matrix.n22, cam.matrix.n32, cam.matrix.n42),(cam.matrix.n13, cam.matrix.n23, cam.matrix.n33, cam.matrix.n43),(cam.matrix.n14, cam.matrix.n24, cam.matrix.n34, cam.matrix.n44)))
            camera_object.matrix_world = global_matrix @ transform_matrix 
            #bpy.context.scene.collection.objects.link(camera_object)
            col.objects.link(camera_object)
        
        for bri in self.scene.Bricks:
            current += 1    

            for pa in bri.Parts:
                currentpart += 1

                if pa.designID not in geometriecache:
                    geo = Geometry(designID=pa.designID, database=self.database)
                    progress(current ,total , "(" + geo.designID + ") " + geo.Partname, ' ')
                    geometriecache[pa.designID] = geo
                    
                else:
                    geo = geometriecache[pa.designID]
                    progress(current ,total , "(" + geo.designID + ") " + geo.Partname ,'-')
                
                # n11=a, n21=d, n31=g, n41=x,
                # n12=b, n22=e, n32=h, n42=y,
                # n13=c, n23=f, n33=i, n43=z,
                # n14=0, n24=0, n34=0, n44=1
                
                # Read out 1st Bone matrix values
                ind = 0
                n11 = pa.Bones[ind].matrix.n11
                n12 = pa.Bones[ind].matrix.n12
                n13 = pa.Bones[ind].matrix.n13
                n14 = pa.Bones[ind].matrix.n14
                n21 = pa.Bones[ind].matrix.n21
                n22 = pa.Bones[ind].matrix.n22
                n23 = pa.Bones[ind].matrix.n23
                n24 = pa.Bones[ind].matrix.n24
                n31 = pa.Bones[ind].matrix.n31
                n32 = pa.Bones[ind].matrix.n32
                n33 = pa.Bones[ind].matrix.n33
                n34 = pa.Bones[ind].matrix.n34
                n41 = pa.Bones[ind].matrix.n41
                n42 = pa.Bones[ind].matrix.n42
                n43 = pa.Bones[ind].matrix.n43
                n44 = pa.Bones[ind].matrix.n44
                
                # Only parts with more then 1 bone are flex parts and for these we need to undo the transformation later
                flexflag = 1
                uniqueId = str(uuid.uuid4().hex)
                material_string = '_' + '_'.join(pa.materials)
                written_obj = geo.designID + material_string
                
                if hasattr(pa, 'decoration'):
                    decoration_string = '_' + '_'.join(pa.decoration)
                    written_obj = written_obj + decoration_string
                
                if (len(pa.Bones) > flexflag):
                    # Flex parts are "unique". Ensure they get a unique filename
                    written_obj = written_obj + "_" + uniqueId
                
                brick_object = bpy.data.objects.new("brick{0}_{1}".format(currentpart, written_obj), None)                
                #bpy.context.scene.collection.objects.link(brick_object)
                col.objects.link(brick_object)
                brick_object.empty_display_size = 1.25
                brick_object.empty_display_type = 'PLAIN_AXES'
                #out.write('''
                #def "brick{0}_{1}" (
                # add references = @./{2}/{1}.usda@ {{\n'''.format(currentpart, written_obj, assetsDir))
            
                if not (len(pa.Bones) > flexflag):
                # Flex parts don't need to be moved, but non-flex parts need
                    #transform_matrix = mathutils.Matrix(((n11, n12, n13, n14),(n21, n22, n23, n24),(n31, n32, n33, n34),(n41, n42, n43, n44)))
                    transform_matrix = mathutils.Matrix(((n11, n21, n31, n41),(n12, n22, n32, n42),(n13, n23, n33, n43),(n14, n24, n34, n44)))

                    # Random Scale for brick seams
                    scalefact = (geo.maxGeoBounding - 0.025 * random.uniform(0.0, 1.000)) / geo.maxGeoBounding

                    # miny used for floor plane later
                    if miny > float(n42):
                        miny = n42
                                            
                #op = open(written_obj + ".usda", "w+")
                #op.write('''#usda 1.0 string name = "brick_{0}"{{\n'''.format(written_obj))
                
                # transform -------------------------------------------------------
                decoCount = 0
                for part in geo.Parts:
                    
                    written_geo = str(geo.designID) + '_' + str(part)
                    
                    geo.Parts[part].outpositions = [elem.copy() for elem in geo.Parts[part].positions]
                    geo.Parts[part].outnormals = [elem.copy() for elem in geo.Parts[part].normals]
                    
                    # translate / rotate only parts with more then 1 bone. This are flex parts
                    if (len(pa.Bones) > flexflag):

                        written_geo = written_geo + '_' + uniqueId
                        for i, b in enumerate(pa.Bones):
                            # positions
                            for j, p in enumerate(geo.Parts[part].outpositions):
                                if (geo.Parts[part].bonemap[j] == i):
                                    p.transform( invert * b.matrix)
                                    
                            # normals
                            for k, n in enumerate(geo.Parts[part].outnormals):
                                if (geo.Parts[part].bonemap[k] == i):
                                    n.transformW( invert * b.matrix)

                    #op.write('\tdef "g{0}" (\n'.format(part))
                    #op.write('\t\tadd references = @./geo{0}.usda@\n\t)\n\t{{\n'.format(written_geo))
                    
                    #gop = open(os.path.join(assetsDir,"geo" + written_geo + ".usda"), "w+")
                    #gop.write('''#usda 1.0 defaultPrim = "geo{0}" def Mesh "mesh{0}" {{\n'''.format(written_geo))
                    
                    mesh = bpy.data.meshes.new("geo{0}".format(written_geo))
                    geo_obj = bpy.data.objects.new(mesh.name, mesh)
                    geo_obj.parent = brick_object
                    col.objects.link(geo_obj)

                    verts = []
                    for point in geo.Parts[part].outpositions:
                        single_vert = mathutils.Vector([point.x, point.y, point.z])
                        verts.append(single_vert)
                    
                    usenormal = True
                    if usenormal == True: # write normals in case flag True
                        # WARNING: SOME PARTS MAY HAVE BAD NORMALS. FOR EXAMPLE MAYBE PART: (85861) PL.ROUND 1X1 W. THROUGHG. HOLE
                        #gop.write('\t\tnormal3f[] normals = [')
                        fmt = ""
                        for normal in geo.Parts[part].outnormals:
                            #gop.write('{0}({1}, {2}, {3})'.format(fmt, normal.x, normal.y, normal.z))
                            fmt = ", "

                    #try catch here for possible problems in materials assignment of various g, g1, g2, .. files in lxf file
                    try:
                        materialCurrentPart = pa.materials[part]
                    except IndexError:
                        print('WARNING: {0}.g{1} has NO material assignment in lxf. Replaced with color 9. Fix {0}.xml faces values.'.format(pa.designID, part))
                        materialCurrentPart = '9'
                    
                    #lddmatri = self.allMaterials.getMaterialRibyId(materialCurrentPart)
                    #matname = materialCurrentPart

                    deco = '0'
                    if hasattr(pa, 'decoration') and len(geo.Parts[part].textures) > 0:
                        if decoCount < len(pa.decoration):
                            deco = pa.decoration[decoCount]
                        decoCount += 1

                    extfile = ''
                    #if not deco == '0':
                    #    extfile = deco + '.png'
                    #    matname += "_" + deco
                    #    decofilename = DECORATIONPATH + deco + '.png'
                    #    if not os.path.isfile(os.path.join(assetsDir, extfile)) and self.database.fileexist(decofilename):
                    #        with open(os.path.join(assetsDir, extfile), "wb") as f:
                    #            f.write(self.database.filelist[decofilename].read())
                    #            f.close()

                    #if not matname in usedmaterials:
                    #    usedmaterials.append(matname)
                    #    outmat = open(os.path.join(assetsDir,"material_" + matname + ".usda"), "w+")
                        
                    #    if not deco == '0':
                    #        outmat.write(lddmatri.string(deco))

                    #    else:
                    #        outmat.write(lddmatri.string(None))
                        
                    #    outmat.close()

                    #op.write('\n\t\tcolor3f[] primvars:displayColor = [({0}, {1}, {2})]\n'.format(lddmatri.r, lddmatri.g, lddmatri.b))
                    #op.write('\t\trel material:binding = <Material{0}/material_{0}a>\n'.format(matname))
                    #op.write('''\t\tdef "Material{0}" (add references = @./material_{0}.usda@'''.format(matname))
                    
                    #gop.write('\t\tint[] faceVertexIndices = [')
                    faces = []
                    for face in geo.Parts[part].faces:
                        single_face = [face.a , face.b, face.c]
                        faces.append(single_face)
                            
                    #gop.write('\n\t\tcolor3f[] primvars:displayColor = [(1, 0, 0)]\n')
                            
                    if len(geo.Parts[part].textures) > 0:
                        
                        #gop.write('\n\t\tfloat2[] primvars:st = [')
                        fmt = ""
                        for text in geo.Parts[part].textures:
                            #gop.write('{0}({1}, {2})'.format(fmt, text.x, (-1) * text.y))
                            fmt = ", "
                            
                        #gop.write('] (\n')
                        #gop.write('\t\t\tinterpolation = "faceVarying"\n')
                        #gop.write('\t\t)\n')
                    
                        #gop.write('\t\tint[] primvars:st:indices = [')
                        fmt = ""
                        for face in geo.Parts[part].faces:
                            #gop.write('{0}{1},{2},{3}'.format(fmt, face.a, face.b, face.c))
                            fmt = ", "
                            #out.write(face.string("f",indexOffset,textOffset))
                    
                    #gop.close()
                    edges = []
                    mesh.from_pydata(verts, edges, faces)
                    for f in mesh.polygons:
                        f.use_smooth = True
                    
                if not (len(pa.Bones) > flexflag):
                    #Transform (move) only non-flex parts
                    brick_object.matrix_world =  global_matrix @ transform_matrix
                    brick_object.scale = (scalefact, scalefact, scalefact)
                    
                else:
                    #Flex parts need only to be aligned to Blenders coordinate system
                    brick_object.matrix_world = global_matrix           

                #Logo on studs
                uselogoonstuds = False
                if uselogoonstuds == True: # write logo on studs in case flag True
                    a = 0
                    for studs in geo.studsFields2D:
                        a += 1
                        if studs.type == 23:
                            for i in range(len(studs.custom2DField)):
                                for j in range(len(studs.custom2DField[0])):
                                    if studs.custom2DField[i][j] in LOGOONSTUDSCONNTYPE: #Valid Connection type which are "allowed" for logo on stud
                                        if not "logoonstuds" in writtenribs:
                                            writtenribs.append("logoonstuds")
                                            #dest = shutil.copy('logoonstuds.usdc', assetsDir) 
                                        #op.write('\tdef "stud{0}_{1}_{2}" (\n'.format(a, i, j))
                                        #op.write('\t\tadd references = @./logoonstuds.usdc@\n\t)\n\t{')
                                        #op.write('\t\tfloat xformOp:rotateY = 180')
                                        #op.write('\n\t\tdouble3 xformOp:translate = ({0}, {1}, {2})'.format(-1 * studs.matrix.n41 + j * 0.4 + 0.0145, -1 * studs.matrix.n42 + 0.14, -1 * studs.matrix.n43 + i * 0.4 - 0)) #Values from trial and error: minx of bounding = -0.4, 0.46 =ty of field + 0.14
                                        #op.write('\n\t\tmatrix4d xformOp:transform = ( ({0}, {1}, {2}, {3}), ({4}, {5}, {6}, {7}), ({8}, {9}, {10}, {11}), ({12}, {13}, {14}, {15}) )'.format(studs.matrix.n11, studs.matrix.n12, -1 * studs.matrix.n13, studs.matrix.n14, studs.matrix.n21, studs.matrix.n22, -1 * studs.matrix.n23, studs.matrix.n24, -1 * studs.matrix.n31, -1 * studs.matrix.n32, studs.matrix.n33, studs.matrix.n34, 0, 0, 0, studs.matrix.n44))
                                        #op.write('\n\t\tdouble3 xformOp:scale = ({0}, {0}, {0})'.format(0.81))
                                        #op.write('\n\t\tuniform token[] xformOpOrder = ["xformOp:transform","xformOp:translate","xformOp:scale", "xformOp:rotateY"]\n')
                                        #op.write('\n\t\tcolor3f[] primvars:displayColor = [({0}, {1}, {2})]\n'.format(lddmatri.r, lddmatri.g, lddmatri.b))
                                        #op.write('\t\trel material:binding = <Material{0}/material_{0}a>\n'.format(matname))
                                        #op.write('''\t\tdef "Material{0}" (add references = @./material_{0}.usda@)'''.format(matname))

                #op.write('}\n')
                # -----------------------------------------------------------------
                #op.close()
                                
                # Reset index for each part
                indexOffset = 1
                textOffset = 1
                
                #out.write('\t\t}\n')
                
                if not written_obj in writtenribs:
                    writtenribs.append(written_obj)
                    #dest = shutil.copy(written_obj + '.usda', assetsDir)
                
                #os.remove(written_obj + '.usda')
        
        useplane = True                
        if useplane == True: # write the floor plane in case True
            i = 0
            #out.write('''def Mesh "GroundPlane_1"'''.format(miny))
        
        #zf.close()
        #zfmat.close()
        #out.write('}\n')
        sys.stdout.write('%s\r' % ('                                                                                                 '))
        print("--- %s seconds ---" % (time.time() - start_time))
        
            
def setDBFolderVars(dbfolderlocation):
    global PRIMITIVEPATH
    global GEOMETRIEPATH
    global DECORATIONPATH
    global MATERIALNAMESPATH
    PRIMITIVEPATH = dbfolderlocation + '/Primitives/'
    GEOMETRIEPATH = dbfolderlocation + '/Primitives/LOD0/'
    DECORATIONPATH = dbfolderlocation + '/Decorations/'
    MATERIALNAMESPATH = dbfolderlocation + '/MaterialNames/'

def FindDatabase():
    lddliftree = os.getenv('LDDLIFTREE')
    if lddliftree is not None:
        if os.path.isdir(str(lddliftree)): #LDDLIFTREE points to folder
            return str(lddliftree)
        elif os.path.isfile(str(lddliftree)): #LDDLIFTREE points to file (should be db.lif)
            return str(lddliftree)
    
    else: #Env variable LDDLIFTREE not set. Check for default locations per different platform.
        if platform.system() == 'Darwin':
            if os.path.isdir(str(os.path.join(str(os.getenv('USERPROFILE') or os.getenv('HOME')),'Library','Application Support','LEGO Company','LEGO Digital Designer','db'))):
                return str(os.path.join(str(os.getenv('USERPROFILE') or os.getenv('HOME')),'Library','Application Support','LEGO Company','LEGO Digital Designer','db'))
            elif os.path.isfile(str(os.path.join(str(os.getenv('USERPROFILE') or os.getenv('HOME')),'Library','Application Support','LEGO Company','LEGO Digital Designer','db.lif'))):
                return str(os.path.join(str(os.getenv('USERPROFILE') or os.getenv('HOME')),'Library','Application Support','LEGO Company','LEGO Digital Designer','db.lif'))
            else:
                print("no LDD database found please install LEGO-Digital-Designer")
                os._exit()
        elif platform.system() == 'Windows':
            if os.path.isdir(str(os.path.join(str(os.getenv('USERPROFILE') or os.getenv('HOME')),'AppData','Roaming','LEGO Company','LEGO Digital Designer','db'))):
                return str(os.path.join(str(os.getenv('USERPROFILE') or os.getenv('HOME')),'AppData','Roaming','LEGO Company','LEGO Digital Designer','db'))
            elif os.path.isfile(str(os.path.join(str(os.getenv('USERPROFILE') or os.getenv('HOME')),'AppData','Roaming','LEGO Company','LEGO Digital Designer','db.lif'))):
                return str(os.path.join(str(os.getenv('USERPROFILE') or os.getenv('HOME')),'AppData','Roaming','LEGO Company','LEGO Digital Designer','db.lif'))
            else:
                print("no LDD database found please install LEGO-Digital-Designer")
                os._exit()
        elif platform.system() == 'Linux':
            if os.path.isdir(str(os.path.join(str(os.getenv('USERPROFILE') or os.getenv('HOME')),'.wine','drive_c','users',os.getenv('USER'),'Application Data','LEGO Company','LEGO Digital Designer','db'))):
                return str(os.path.join(str(os.getenv('USERPROFILE') or os.getenv('HOME')),'.wine','drive_c','users',os.getenv('USER'),'Application Data','LEGO Company','LEGO Digital Designer','db'))
            elif os.path.isfile(str(os.path.join(str(os.getenv('USERPROFILE') or os.getenv('HOME')),'.wine','drive_c','users',os.getenv('USER'),'Application Data','LEGO Company','LEGO Digital Designer','db.lif'))):
                return str(os.path.join(str(os.getenv('USERPROFILE') or os.getenv('HOME')),'.wine','drive_c','users',os.getenv('USER'),'Application Data','LEGO Company','LEGO Digital Designer','db.lif'))
            else:
                print("no LDD database found please install LEGO-Digital-Designer")
                os._exit()
        else:
            print('Your OS {0} is not supported yet.'.format(platform.system()))
            os._exit()
    
def progress(count, total, status='', suffix = ''):
    bar_len = 40
    filled_len = int(round(bar_len * count / float(total)))
    percents = round(100.0 * count / float(total), 1)
    bar = '#' * filled_len + '-' * (bar_len - filled_len)
    sys.stdout.write('Progress: [%s] %s%s %s %s\r' % (bar, percents, '%', suffix, '                                                 '))
    sys.stdout.write('Progress: [%s] %s%s %s %s\r' % (bar, percents, '%', suffix, status))
    sys.stdout.flush()

def main():
    print("- - - pylddlib - - -")
    print("          _ ")
    print("         [_]")
    print("       /|   |\\")
    print("      ()'---' C")
    print("        | | |")
    print("        [=|=]")
    print("")
    print("- - - - - - - - - - - -")
    try:
        lxf_filename = sys.argv[1]
        obj_filename = sys.argv[2]
    except Exception as e:
        print("Missing Paramenter:" + sys.argv[0] + " infile.lfx exportname (without extension)")
        return

    converter = Converter()
    if os.path.isdir(FindDatabase()):
        print("Found DB folder. Will use this instead of db.lif!")
        setDBFolderVars(dbfolderlocation = FindDatabase())
        converter.LoadDBFolder(dbfolderlocation = FindDatabase())
        converter.LoadScene(filename=lxf_filename)
        converter.Export(filename=obj_filename)
        
    elif os.path.isfile(FindDatabase()):
        print("Found db.lif. Will use this.")
        converter.LoadDatabase(databaselocation = FindDatabase())
        converter.LoadScene(filename=lxf_filename)
        converter.Export(filename=obj_filename)
    else:
        print("no LDD database found please install LEGO-Digital-Designer")














def read_some_data(context, filepath, use_some_setting):
    #print("running read_some_data...")
    #f = open(filepath, 'r', encoding='utf-8')
    #data = f.read()
    #f.close()

    # would normally load the data here
    #print(data)
    
    
    
    converter = Converter()
    if os.path.isdir(FindDatabase()):
        print("Found DB folder. Will use this instead of db.lif!")
        setDBFolderVars(dbfolderlocation = FindDatabase())
        converter.LoadDBFolder(dbfolderlocation = FindDatabase())
        converter.LoadScene(filename=filepath)
        converter.Export(filename=filepath)
        
    elif os.path.isfile(FindDatabase()):
        print("Found db.lif. Will use this.")
        converter.LoadDatabase(databaselocation = FindDatabase())
        converter.LoadScene(filename=filepath)
        converter.Export(filename=filepath)
    else:
        print("no LDD database found please install LEGO-Digital-Designer")

    return {'FINISHED'}


# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

class ImportLDDOps(Operator, ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_description  = "Import LEGO Digital Designer scenes (.lxf/.lxfml)"
    bl_idname = "import_scene.importldd"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import LDD scene"

    # ImportHelper mixin class uses this
    filename_ext = ".lxf"

    filter_glob: StringProperty(
        default="*.lxf;*.lxfml",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    lddPath: StringProperty(
        name="",
        description="Full filepath to the LDD db folder / db.lif file",
        default=FindDatabase(),
    ) 
    
    use_setting: BoolProperty(
        name="Example Boolean",
        description="Example Tooltip",
        default=True,
    )
    
    useLogoStuds: BoolProperty(
        name="Show 'LEGO' logo on studs",
        description="Shows the LEGO logo on each stud (at the expense of some extra geometry and import time)",
        default=False,
    )

    useCamera: BoolProperty(
        name="Import camera(s)",
        description="Import camera(s) from LEGO Digital Designer",
        default=True,
    )

    type: EnumProperty(
        name="Example Enum",
        description="Choose between two items",
        items=(
            ('OPT_A', "First Option", "Description one"),
            ('OPT_B', "Second Option", "Description two"),
        ),
        default='OPT_A',
    )

    def execute(self, context):
        return read_some_data(context, self.filepath, self.use_setting)


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportLDDOps.bl_idname, text="LEGO Digital Designer (.lxf/.lxfml)")


def register():
    bpy.utils.register_class(ImportLDDOps)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportLDDOps)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    register()

    # test call
    bpy.ops.import_scene.importldd('INVOKE_DEFAULT')
