# SCAR - Serverless Container-aware ARchitectures
# Copyright (C) 2011 - GRyCAP - Universitat Politecnica de Valencia
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import abc
from enum import Enum

class CallType(Enum):
    INIT = "init"
    INVOKE = "invoke"
    RUN = "run"
    UPDATE = "update"    
    LS = "ls"
    RM = "rm"
    LOG = "log"
    PUT = "put"
    GET = "get"  

class Commands(metaclass=abc.ABCMeta):
    ''' All the different cloud provider controllers must inherit 
    from this class to ensure that the commands are defined consistently'''

    @abc.abstractmethod
    def init(self):
        pass

    @abc.abstractmethod    
    def invoke(self):
        pass
    
    @abc.abstractmethod    
    def run(self):
        pass
    
    @abc.abstractmethod    
    def update(self):
        pass    
    
    @abc.abstractmethod    
    def ls(self):
        pass
    
    @abc.abstractmethod
    def rm(self):
        pass

    @abc.abstractmethod
    def log(self):
        pass
    
    @abc.abstractmethod
    def put(self):
        pass
    
    @abc.abstractmethod
    def get(self):
        pass    
    
    @abc.abstractmethod
    def parse_arguments(self, args):
        pass    
