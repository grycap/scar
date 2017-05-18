import argparse

version = "v0.0.1"

def check_memory(lambda_memory):
    """ Check if the memory intrduced by the user is correct.
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

class Scar(object):
    """Implements most of the command line interface.
    These methods correspond directly to the commands that can
    be invoked via the command line interface.
    """

    def __init__(self):
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
        if args.memory:
            check_memory(args.memory)
        if args.time:
            check_time(args.time)
        
        print (args)
        
    def ls(self, args):
        print (args)
        
    def run(self, args):
        print (args)
            
    def rm(self, args):
        print (args)

    def log(self, args):
        print (args)
    
    def version(self, args):
        print ("scar " + version)
        
        
        
if __name__ == "__main__":
    Scar().execute()        
