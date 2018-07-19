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
