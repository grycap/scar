Scar container
==============

Other option to use SCAR is to create the container with the binaries included or to use the already available image with the packaged binaries installed from `grycap/scar <https://hub.docker.com/r/grycap/scar/>`_. Either you want to build the images from scratch or you want to use the already available image you will need `docker <https://www.docker.com/community-edition#/download>`_ installed in your machine.

Building the SCAR image
^^^^^^^^^^^^^^^^^^^^^^^

All the steps needed to build the SCAR image are defined in the `Dockerfile <https://github.com/grycap/scar/blob/master/Dockerfile>`_ available at the root of the project. You only need to execute::

  docker build -t scar -f Dockerfile .

This command creates a scar image in your docker repository that can be launched as::

  docker run -it -v $AWS_CREDENTIALS_FOLDER:/home/scar/.aws -v $SCAR_CONFIG_FOLDER:/home/scar/.scar scar

With the previous command we tell docker to mount the SCAR required folders (`~/.aws` and `~/.scar`) in the paths expected by the binary.
Launching the container with the command described above also allow us to have different configuration folders wherever we want in our host machine.

Once we are inside the container you can execute SCAR like another system binary::

  scar init -n scar-cowsay -i grycap/cowsay

  scar run -n scar-cowsay

  Request Id: 91e8afb6-8f19-11e8-9167-bd8a0b8b0f78
  Log Group Name: /aws/lambda/scar-cowsay
  Log Stream Name: 2018/07/24/[$LATEST]08444e77d6a14b09a47de0d5e4af5fa8
   _________________________________________
  < Quick!! Act as if nothing has happened! >
   -----------------------------------------
          \   ^__^
           \  (oo)\_______
              (__)\       )\/\
                  ||----w |
                  ||     ||

  scar ls

  NAME           MEMORY    TIME  IMAGE_ID       API_URL
  -----------  --------  ------  -------------  ---------
  scar-cowsay       512     300  grycap/cowsay  -

  scar rm -n scar-cowsay

