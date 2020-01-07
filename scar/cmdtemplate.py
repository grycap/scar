# Copyright (C) GRyCAP - I3M - UPV
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from enum import Enum
import abc

class CallType(Enum):
    INIT = "init"
    INVOKE = "invoke"
    RUN = "run"
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
