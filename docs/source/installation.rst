Installation
============
If you want to avoid installing packages you can launch a docker container with scar installed. 
Please check the :doc:`/scar_container` section.

SCAR requires python3, pip3 and a configured AWS credentials file in your system.
More info about the AWS credentials file can be found `here <https://docs.aws.amazon.com/cli/latest/userguide/cli-config-files.html>`_.

You have to options when installing SCAR.
You can use pip3 or you can clone the GitHub repository and install the required dependencies.

Install using pip3
^^^^^^^^^^^^^^^^^^
2) Install SCAR using the PyPI package with the command::

    pip3 install scar
   
   This will also creates an script in your local bin folder so you can execute the scar commands directly like:  ``scar ls``

Clone the Github Repository
^^^^^^^^^^^^^^^^^^^^^^^^^^^
1) Clone the GitHub repository::

    git clone https://github.com/grycap/scar.git
    cd scar

2) Install the Python required dependencies automatically with the command::

    pip3 install -r requirements.txt
    
3) Execute the SCAR cli with the command::

    python3 scar/scarcli.py ...

3) (Optional) Define an alias for easier usability::

    alias scar='python3 `pwd`/scar/scarcli.py'

Extra dependencies
^^^^^^^^^^^^^^^^^^
The last dependencies need to be installed using the package manager of your distribution (apt in this case)::
  
    sudo apt -y install zip unzip