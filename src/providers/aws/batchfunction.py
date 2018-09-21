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

from .iam import IAM
from botocore.exceptions import ClientError
from src.providers.aws.cloudwatchlogs import CloudWatchLogs
from src.providers.aws.botoclientfactory import GenericClient
import src.logger as logger
import src.utils as utils


class Batch(GenericClient):

    lambda_properties = {}
    batch_properties = {}
    iam_properties={}
    aws_properties={}
    def __init__(self, aws_properties):
        GenericClient.__init__(self, aws_properties)
        self.aws_properties= aws_properties
        self.lambda_properties = aws_properties['lambda']
        self.batch_properties = aws_properties['batch']
        self.iam_properties = aws_properties['iam']    
    
    @utils.lazy_property
    def cloudwatch_logs(self):
        cloudwatch_logs = CloudWatchLogs(self.aws_properties)
        return cloudwatch_logs

    def existe_compute_environments(self,name):
        creation_args = self.get_describe_compute_env_args(name_c=name)
        response=self.client.describe_compute_environments(**creation_args)
        if (len(response["computeEnvironments"])>0):
            return True
        else:
            return False

    def delete_compute_environment(self,name):
        temp = True
        while(temp):
            creation_args = self.get_describe_job_queue_args(name_j=name)
            response=self.client.describe_job_queues(**creation_args)                
            state=response["jobQueues"][0]["state"]
            status= response["jobQueues"][0]["status"]
            if(state=="ENABLED" and status=="VALID"):
                updating_args = self.get_update_job_queue_args(name_j=name)
                response = self.client.update_job_queue(**updating_args)
            else:
                if(state=="DISABLED" and status=="VALID"):
                    deleting_args = self.get_delete_job_queue_args(name_j=name)
                    response = self.client.delete_job_queue(**deleting_args)
                    temp = False
        temp = True

        while(temp):
            creation_args = self.get_describe_compute_env_args(name_c=name)
            response=self.client.describe_compute_environments(**creation_args)
            state=response["computeEnvironments"][0]["state"]
            status= response["computeEnvironments"][0]["status"]                                
            if(state=="ENABLED"):
                update_args= self.get_update_compute_env_args(name_c=name)
                response = self.client.update_compute_environment(**update_args)
            else:
                if(state=="DISABLED" and status=="VALID" and (not self.exist_jobs_queue(name))):
                    delete_args= self.get_delete_compute_env_args(name_c=name)
                    response = self.client.delete_compute_environment(**delete_args)
                    temp = False
                    logger.error("Compute enviroment deleted") 

    def get_creations_compute_env_args(self):
        return {'computeEnvironmentName' : self.lambda_properties['name'],
                'serviceRole' : self.iam_properties['role'],
                'type' : self.batch_properties['type'],
                'state' :  self.batch_properties['state'],
                'computeResources':{
                    'subnets' : self.batch_properties['subnets'],
                    'instanceRole' : self.batch_properties['instanceRole'],
                    'instanceTypes': self.batch_properties['instanceTypes'],
                    'maxvCpus': self.batch_properties['maxvCpus'],
                    'minvCpus': self.batch_properties['minvCpus'],
                    'desiredvCpus': self.batch_properties['desiredvCpus'],
                    'securityGroupIds': self.batch_properties['securityGroupIds'],
                    'type': self.batch_properties['type_inst'],
                    },
                }
    def get_creations_job_queue_args(self):
        return { 
            'computeEnvironmentOrder':[{'computeEnvironment': self.lambda_properties["name"],'order': 1},],
            'jobQueueName': self.lambda_properties["name"],
            'priority':1,
            'state':self.batch_properties['state'],
        }
    def get_describe_compute_env_args(self,name_c=None):
        if name_c:
            return {'computeEnvironments':[name_c,],}
        else:    
            return {'computeEnvironments':[self.lambda_properties["name"],],}
    
    def get_describe_job_queue_args(self,name_j=None):
        if name_j:
            return {'jobQueues':[name_j,],}
        else:    
            return {'jobQueues':[self.lambda_properties["name"],],}
    
    def get_update_job_queue_args(self,name_j=None):
        if name_j:
            return {'jobQueue':name_j,'state':'DISABLED'}
        else:    
            return {'jobQueue':self.lambda_properties["name"],'state':'DISABLED',}

    def get_update_compute_env_args(self,name_c=None):
        if name_c:
            return {'computeEnvironment':name_c,'state':'DISABLED'}
        else:    
            return {'computeEnvironment':self.lambda_properties["name"],'state':'DISABLED',}
    
    def get_delete_job_queue_args(self,name_j=None):
        if name_j:
            return {'jobQueue':name_j,}
        else:    
            return {'jobQueue':self.lambda_properties["name"],}

    def get_delete_compute_env_args(self,name_c=None):
        if name_c:
            return {'computeEnvironment':name_c,}
        else:    
            return {'computeEnvironment':self.lambda_properties["name"],}

    def get_describe_job_args(self,idJob):
        return {'jobs':[idJob,],}
            
        

    def exist_jobs_queue(self,name):
        describe_args = self.get_describe_job_queue_args(name_j=name)
        response = self.client.describe_job_queues(**describe_args)
        if (len(response["jobQueues"])==0):
            return False
        else:
            return True
    def  exist_job(self, name):
        describe_args = self.get_describe_job_args(name)
        response = self.client.describe_jobs(**describe_args)
        if (len(response["jobs"])==0):
            return False
        else:
            return True
    def get_logs_job(self, name):
        describe_args = self.get_describe_job_args(name)
        response = self.client.describe_jobs(**describe_args)
        if(response["jobs"][0]["status"]=="SUCCEEDED"):
            full_log = " "
            events = self.cloudwatch_logs.get_logs_batch("/aws/batch/job",response["jobs"][0]["container"]["logStreamName"])["events"]
            for event in events:
                full_log += event['message']+"\n"
        else:
            full_log = "status: "+response["jobs"][0]["status"]                            
        return full_log




    def create_compute_environment(self):
        creation_args = self.get_creations_compute_env_args()
        self.client.create_compute_environment(**creation_args)
        temp = True
        while(temp):
            creation_args = self.get_describe_compute_env_args()
            response=self.client.describe_compute_environments(**creation_args)
            state=response["computeEnvironments"][0]["state"]
            status= response["computeEnvironments"][0]["status"]
            if (state == "ENABLED" and status=="VALID"):
                creation_args = self.get_creations_job_queue_args()
                response= self.client.create_job_queue(**creation_args)
                temp = False
        logger.error("Compute environment created.")


    
            

