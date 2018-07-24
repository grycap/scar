Installation
============

If you want to avoid installing packages and you can launch docker containers check the :doc:`/scar_container` section.

1) SCAR requires python3, pip3 and a configured AWS credentials file in your system.
   More info about the AWS credentials file can be found `here <https://docs.aws.amazon.com/cli/latest/userguide/cli-config-files.html>`_.

2) Clone the GitHub repository::

    git clone https://github.com/grycap/scar.git
    cd scar

3) Install the python required dependencies automatically with the command::

    sudo pip3 install -r requirements.txt

  The last dependency needs to be installed using the apt manager::
  
    sudo apt install zip


4) (Optional) Define an alias for easier usability::

    alias scar='python3 `pwd`/scar.py'