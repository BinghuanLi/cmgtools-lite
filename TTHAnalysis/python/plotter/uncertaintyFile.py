#!/usr/bin/env python
from math import *
import re
import os, os.path
from array import array
from copy import *

from CMGTools.TTHAnalysis.plotter.fakeRate import *

class Uncertainty:
    def __init__(self,name,procmatch,binmatch,unc_type,extra_args={}):
        self.name = name
        self._procmatch = procmatch
        self._binmatch = binmatch
        self.unc_type = unc_type
        self.extra_args = extra_args
        self.fakerate = [FakeRate(''),FakeRate('')]
        self.fakerate[0]._weight = '1'
        self.fakerate[1]._weight = '1'
        self.trivialFunc=[None,None]
        self.normUnc=[None,None]
        self.prepFR()

    def prepFR(self):

        if self.unc_type=='templateAsymm':
            for idx in xrange(2):
                if 'FakeRate' in self.extra_args[idx]:
                    self.fakerate[idx] = FakeRate(self.extra_args[idx]['FakeRate'])
                if 'AddWeight' in self.extra_args[idx]:
                    self.fakerate[idx]._weight = '(%s)*(%s)'%(self.fakerate[idx]._weight,self.extra_args[idx]['AddWeight'])

        elif self.unc_type=='templateSymm':
            self.fakerate[1] = None
            self.trivialFunc[1] = 'symmetrize_up_to_dn'
            idx=0
            if 'FakeRate' in self.extra_args[idx]:
                self.fakerate[idx] = FakeRate(self.extra_args[idx]['FakeRate'])
            if 'AddWeight' in self.extra_args[idx]:
                self.fakerate[idx]._weight = '(%s)*(%s)'%(self.fakerate[idx]._weight,self.extra_args[idx]['AddWeight'])

        elif self.unc_type=='normAsymm':
            self.fakerate = [None,None]
            self.trivialFunc = ['apply_norm_up','apply_norm_dn']
            for idx in xrange(2):
                if 'NormFactor' in self.extra_args[idx]: self.normUnc[idx] = float(self.extra_args[idx]['NormFactor'])
                else: self.normUnc[idx] = 1

        elif self.unc_type=='normSymm':
            self.fakerate = [None,None]
            self.trivialFunc = ['apply_norm_up','apply_norm_dn']
            idx=0
            if 'NormFactor' in self.extra_args[idx]:
                self.normUnc[idx] = float(self.extra_args[idx]['NormFactor'])
                self.normUnc[1] = 1.0/self.normUnc[0]
            
        else: raise RuntimeError, 'Uncertainty type not recognised'
            
    def isTrivial(self,sign):
        return (self.getFR(sign)==None)
    def getTrivial(self,sign,results):
        idx = 0 if sign=='up' else 1
        if self.getFR(sign) or (self.trivialFunc[idx]==None): raise RuntimeError
        return getattr(self,self.trivialFunc[idx])(results)
    def isNorm(self):
        return (self.normUnc!=[None,None])

    def symmetrize_up_to_dn(self,results):
        central, up, down = results
        h = central.Clone('');
        h.Multiply(h)
        h.Divide(up)
        return h
    def apply_norm_up(self,results):
        return self.apply_norm('up',results)
    def apply_norm_dn(self,results):
        return self.apply_norm('dn',results)
    def apply_norm(self,sign,results):
        central, up, down = results
        h = central.Clone('')
        h.Scale(self.normUnc[0] if sign=='up' else self.normUnc[1])
        return h

    def procmatch(self):
        return self._procmatch
    def binmatch(self):
        return self._binmatch
    def unc_type(self):
        return self.unc_type
    def getFR(self,sign):
        if sign=='up': return self.fakerate[0]
        elif sign=='dn': return self.fakerate[1]
        else: raise RuntimeError
    def __str__(self):
        return ' : '.join([self.name,self._procmatch.pattern,self._binmatch.pattern,self.unc_type])+'\n'

class UncertaintyFile:
    def __init__(self,txtfileOrUncertainty):
        if type(txtfileOrUncertainty) == list:
            self._uncertainty = deepcopy(txtfileOrUncertainty[:])
        elif isinstance(txtfileOrUncertainty,UncertaintyFile):
            self._uncertainty = deepcopy(txtfileOrUncertainty.uncertainty())
        else:
            self._uncertainty = []
            file = open(txtfileOrUncertainty, "r")
            if not file: raise RuntimeError, "Cannot open "+txtfileOrUncertainty+"\n"
            for line in file:
              try:
                line = line.strip()
                if len(line) == 0 or line[0] == '#': continue
                line = re.sub(r"(?<!\\)#.*","",line)  ## regexp black magic: match a # only if not preceded by a \!
                line = line.replace(r"\#","#")        ## and now we just unescape the remaining #'s
                while line[-1] == "\\":
                    line = line[:-1] + " " + file.next().strip()
                    line = re.sub(r"(?<!\\)#.*","",line)  ## regexp black magic: match a # only if not preceded by a \!
                    line = line.replace(r"\#","#")        ## and now we just unescape the remaining #'s
                field = [f.strip() for f in line.split(':')]
                (name, procmatch, binmatch, unc_type) = field[:4]
                procmatch = re.compile(procmatch+'$')
                binmatch = re.compile(binmatch+'$')

                def getSettings(_this_f):
                    extra = {}
                    for setting in [f.replace(';',',').strip() for f in _this_f.replace('\\,',';').split(',')]:
                        if "=" in setting:
                            (key,val) = [f.strip() for f in setting.split("=")]
                            extra[key] = eval(val)
                        else: extra[setting] = True
                    return extra
                self._uncertainty.append(Uncertainty(name,procmatch,binmatch,unc_type,[getSettings(_f) for _f in field[4:]]))

              except ValueError, e:
                print "Error parsing cut line [%s]" % line.strip()
                raise 
    def __str__(self):
        newstring = ""
        for u in self._uncertainty:
            newstring += u.__str__()
        return newstring[:-1]
    def uncertainty(self):
        return self._uncertainty[:]
    def add(self,uncertainty):
        if uncertainty.name in [u.name for u in self._uncertainty]: raise RuntimeError, 'Uncertainty with name %s is already present' % uncertainty.name
        self._uncertainty.append(uncertainty)