API Gateway Integration
=======================

Define an HTTP endpoint
-----------------------

SCAR allows to transparently integrate an HTTP endpoint with a Lambda function. To enable this functionality you only need to define an api name and SCAR will take care of the integration process (before using this feature make sure you have to correct rights set in your aws account).

The following configuration file creates a generic api endpoint that redirects the http petitions to your lambda function::

  cat >> api-cow.yaml << EOF
    functions:
      scar-cowsay:
        image: grycap/cowsay
        api_gateway:
          name: cow-api
  EOF

  scar init -f api-cow.yaml

After the function is created you can check the API URL with the command::

  scar ls

That shows the basic function properties::

  NAME                   MEMORY    TIME  IMAGE_ID          API_URL
  -------------------  --------  ------  ----------------  ------------------------------------------------------------------
  scar-cowsay               512     300  grycap/cowsay     https://r8c55jbfz9.execute-api.us-east-1.amazonaws.com/scar/launch


GET Request
-----------

SCAR also allows you to make an HTTP request, for that you can use the command `invoke` like this::

  scar invoke -f api-cow.yaml

This command automatically creates a `GET` request and passes the petition to the API endpoint defined previously.
Bear in mind that the timeout for the api gateway requests is 29s, so if the function takes more time to respond, the api will return an error message.
To launch asynchronous functions you only need to add the `asynch` parameter to the call::

  scar invoke -f api-cow.yaml -a

However, remember that when you launch an asynchronous function throught the API Gateway there is no way to know if the function finishes successfully until you check the function invocation logs.

POST Request
------------

You can also pass files through the HTTP endpoint using the following command::

  cat >> api-cow.yaml << EOF
    functions:
      scar-cowsay:
        image: grycap/cowsay
        data_binary: /tmp/img.jpg
        api_gateway:
          name: cow-api
  EOF

  scar invoke -f api-cow.yaml

or::

  scar invoke -n scar-cowsay -db /tmp/img.jpg

The file specified after the parameter ``-db`` is codified and passed as the POST body.
Take into account that the file limitations for request response and asynchronous requests are 6MB and 128KB respectively, as specified in the `AWS lambda documentation <https://docs.aws.amazon.com/lambda/latest/dg/limits.html>`_.

Lastly, You can also submit JSON as the body to the HTTP endpoint with no other configuration, as long Content-Type is application/json. If SCAR sees a JSON body, it will write this body to /tmp/{REQUEST_ID}/api_event.json. Otherwise, it will default the post body to it being a file.


Passing parameters in the requests
----------------------------------

You can add parameters to the invocations adding the parameters to the configuration file like this::

  cat >> api-cow.yaml << EOF
    functions:
      scar-cowsay:
        image: grycap/cowsay
        api_gateway:
          name: cow-api
          parameters:
            test1: 45
            test2: 69
  EOF

  scar invoke -f api-cow.yaml

or::

  scar invoke -n scar-cowsay -p '{"key1": "value1", "key2": "value3"}'

