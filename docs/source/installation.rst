Installation
============

1) SCAR requires python3, first make sure you have python3 available in your system

2) Clone the GitHub repository::

    git clone https://github.com/grycap/scar.git

3) Install the required dependencies:

  * `zip <https://linux.die.net/man/1/zip>`_ (linux package)
  * `Boto3 <https://pypi.org/project/boto3/>`_ (v1.4.4+ is required)
  * `Tabulate <https://pypi.python.org/pypi/tabulate>`_
  * `Requests <https://pypi.org/project/requests/>`_

  You can automatically install the python dependencies by issuing the following command::

      sudo pip install -r requirements.txt

  The zip package can be installed using apt::

      sudo apt install zip


4) (Optional) Define an alias for increased usability::

    alias scar='python3 `pwd`/scar.py'
