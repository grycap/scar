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

import abc

class GenericValidator(metaclass=abc.ABCMeta):
    ''' All the different cloud provider validators must inherit 
    from this class to ensure that the commands are defined consistently'''

    @classmethod
    def validate(cls):
        '''
        A decorator that wraps the passed in function and validates the dictionary parameters passed
        '''
        def decorator(func):
            def wrapper(*args, **kwargs):
                cls.validate_kwargs(**kwargs)
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    @classmethod
    @abc.abstractmethod
    def validate_kwargs(**kwargs):
        pass
