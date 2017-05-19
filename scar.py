import argparse
import boto3
import zipfile
import os
import shutil
from tabulate import tabulate
import base64

version = "v0.0.1"
dir_path = os.path.dirname(os.path.realpath(__file__))
lambda_name = "scar_function"
zif_file_path = dir_path+'/function.zip'

def check_memory(lambda_memory):
    """ Check if the memory introduced by the user is correct.
    If the memory is not specified in 64mb increments, 
    transforms the request to the next available increment."""
    if (lambda_memory < 128) or (lambda_memory > 1536):
        raise Exception('Incorrect memory size specified')       
    else:
        res = lambda_memory % 64
        if (res == 0):
            return lambda_memory
        else:
            return lambda_memory - res + 64
            
        
def check_time(lambda_time):
    if (lambda_time <= 0) or (lambda_time > 300):
        raise Exception('Incorrect time specified')
    return lambda_time

def create_zip_file(file_name=lambda_name):
    # Set generic lambda function name
    function_name = file_name+'.py'
    # Copy file to avoid messing with the repo files
    shutil.copy(dir_path+'/src/scarsupervisor.py',function_name)
    # Zip the function file
    with zipfile.ZipFile(zif_file_path, 'w') as zf:
        zf.write(function_name)
        os.remove(function_name)
    # Return the zip as an array of bytes
    with open(zif_file_path, 'rb') as f:
        return f.read()
    
def load_payload(payload):
    with open(payload, 'rb') as f:
        return f.read()   

class Scar(object):
    """Implements most of the command line interface.
    These methods correspond directly to the commands that can
    be invoked via the command line interface.
    """

    def __init__(self):
        
        self.create_boto3_client()
        self.create_command_parser()               
    
    def init_lambda_fuction_parameters(self):
        self.lambda_name = lambda_name
        self.lambda_runtime = "python2.7"
        self.lambda_handler = self.lambda_name+".lambda_handler"        
        self.lambda_role = "arn:aws:iam::974349055189:role/lambda-s3-execution-role"        
        self.lambda_env_variables = {"Variables" : {"UDOCKER_DIR":"/tmp/home/.udocker"}}
        self.lambda_zip_file_base64 = {"ZipFile": create_zip_file()}
        self.lambda_memory = 128
        self.lambda_time = 3
        self.lambda_description = "Automatically generated lambda function"

    def create_boto3_client(self):
        self.boto3_client = boto3.client('lambda', region_name='us-east-1')

    def create_command_parser(self):
        self.parser = argparse.ArgumentParser(prog="scar",
                                              description="Deploy containers in serverless architectures",
                                              epilog="Run 'scar COMMAND --help' for more information on a command.")
        subparsers = self.parser.add_subparsers(title='Commands')
                
        # 'init' command
        parser_init = subparsers.add_parser('init', help="Create lambda function")
        # Set default function
        parser_init.set_defaults(func=self.init)
        # Set the positional arguments
        parser_init.add_argument("image_id", help="Container image id (i.e. centos:7)") 
        # Set the optional arguments
        parser_init.add_argument("-d", "--description", help="Lambda function description.")        
        parser_init.add_argument("-n", "--name", help="Lambda function name")
        parser_init.add_argument("-m", "--memory", type=int, help="Lambda function memory in megabytes. Range from 128 to 1536 in increments of 64")
        parser_init.add_argument("-t", "--time", type=int, help="Lambda function maximum execution time in seconds. Max 300.")
    
        # 'ls' command
        parser_ls = subparsers.add_parser('ls', help="List lambda functions")
        parser_ls.set_defaults(func=self.ls)
        
        # 'run' command
        parser_run = subparsers.add_parser('run', help="Deploy function")
        parser_run.set_defaults(func=self.run)
        parser_run.add_argument("name", help="Lambda function name")
        parser_run.add_argument("-m", "--memory", type=int, help="Lambda function memory in megabytes. Range from 128 to 1536 in increments of 64")
        parser_run.add_argument("-t", "--time", type=int, help="Lambda function maximum execution time in seconds. Max 300.")
        parser_run.add_argument("--async", help="Tell Scar to wait or not for the lambda function return", action="store_true")
        parser_run.add_argument("-p", "--payload", nargs='?', type=argparse.FileType('rb'), help="Path to the input file passed to the function")        
        
        # Create the parser for the 'rm' command
        parser_rm = subparsers.add_parser('rm', help="Delete function")
        parser_rm.set_defaults(func=self.rm)
        parser_rm.add_argument("name", help="Lambda function name")
        
        # 'log' command
        parser_log = subparsers.add_parser('log', help="Show the logs for the lambda function")
        parser_log.set_defaults(func=self.log)
        parser_log.add_argument("name", help="Lambda function name")       

        # Create the parser for the 'version' command
        parser_version = subparsers.add_parser('version', help="Show the Scar version information")
        parser_version.set_defaults(func=self.version) 
    
    def execute(self):
        """Command parsing and selection"""
        args = self.parser.parse_args()
        args.func(args)

    def init(self, args):
        self.init_lambda_fuction_parameters()
        
        if args.name:
            self.lambda_name = args.name
            self.lambda_handler = self.lambda_name+".lambda_handler"
            self.lambda_zip_file_base64 = {"ZipFile": create_zip_file(args.name)}  
        if args.memory:
            self.lambda_memory = check_memory(args.memory)
        if args.time:
            self.lambda_time = check_time(args.time)
        if args.description:
            self.lambda_description = args.description            
           
        response = self.boto3_client.create_function( FunctionName=self.lambda_name,
                                                      Runtime=self.lambda_runtime,
                                                      Role=self.lambda_role,
                                                      Handler=self.lambda_handler,
                                                      Code=self.lambda_zip_file_base64,
                                                      Environment=self.lambda_env_variables,
                                                      Description=self.lambda_description,
                                                      Timeout=self.lambda_time,
                                                      MemorySize=self.lambda_memory )
        # Remove the zip created in the operation
        os.remove(zif_file_path)
        print (response)
        
    def ls(self, args):
        paginator = self.boto3_client.get_paginator('list_functions')        
        headers = ['NAME', 'MEMORY', 'TIME']
        table = []
        for functions in paginator.paginate():         
            for lfunction in functions['Functions']:
                table.append([lfunction['FunctionName'], lfunction['MemorySize'], lfunction['Timeout']])            
        print (tabulate(table, headers))
        
    def run(self, args):
        
        invocation_type = 'RequestResponse'
        log_type = 'Tail'
        if args.async:
            invocation_type= 'Event'
            log_type = 'None'
            
        response = self.boto3_client.invoke( FunctionName=args.name,
                                             InvocationType=invocation_type,
                                             LogType=log_type,
                                             Payload=args.payload.read() )
        
        result = base64.b64decode(response['LogResult'])
        print (result.decode("utf-8"))
         
            
    def rm(self, args):
        if args.name:
            response = self.boto3_client.delete_function(FunctionName=args.name)
            print(response)

    def log(self, args):
        print (args)
    
    def version(self, args):
        print ("scar " + version)
               
if __name__ == "__main__":
    Scar().execute()        
