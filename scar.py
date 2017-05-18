import argparse

version="v0.0.1"

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
                
        # Create the parser for the 'run' command
        parser_run = subparsers.add_parser('run', help="Deploy function")
        # Set the positional arguments
        parser_run.add_argument("container_id", help="Execute container")
        # Set the optional arguments 
        parser_run.add_argument("-ak", "--aws_access_key", help="AWS access key")
        parser_run.add_argument("-sk", "--aws_secret_key", help="AWS secret access key")
        # Set default function
        parser_run.set_defaults(func=self.run)
        
        # Create the parser for the 'rm' command
        parser_rm = subparsers.add_parser('rm', help="Delete function")
        # Set the positional arguments
        parser_rm.add_argument("container_id")
        # Set default function
        parser_rm.set_defaults(func=self.rm)
        
        # Create the parser for the 'version' command
        parser_version = subparsers.add_parser('version', help="Show the Scar version information")
        # Set default function
        parser_version.set_defaults(func=self.version)        
                         
    def execute(self):
        """Command parsing and selection"""
        args = self.parser.parse_args()
        args.func(args)

    def run(self, args):
        print "run " + args.container_id
            
    def rm(self, args):
        print "rm " + args.container_id
        
    def version(self, args):
        print "scar " + version
        
if __name__ == "__main__":
    Scar().execute()        