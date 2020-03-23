# Running Audio Classifier on AWS Batch through SCAR

You can run [Audio Classifier](https://marketplace.deep-hybrid-datacloud.eu/modules/deep-oc-audio-classification-tf.html) in AWS Batch via [SCAR](https://github.com/grycap/scar) using the [deephdc/deep-oc-audio-classification-tf](https://hub.docker.com/r/deephdc/deep-oc-audio-classification-tf) Docker image, based on [Tensorflow](https://www.tensorflow.org/).

[Audio Classifier](https://marketplace.deep-hybrid-datacloud.eu/modules/deep-oc-audio-classification-tf.html) is a plug-and-play tool to perform audio classification with Deep Learning. It allows the user to classify their samples of audio as well as training their own classifier for a custom problem. This model is part of a set of models available in the  [DEEP Open Catalog](https://marketplace.deep-hybrid-datacloud.eu/). These models are integrated with the [DEEPaaS API](https://github.com/indigo-dc/DEEPaaS) platform to which the functionality of obtaining the prediction through the command line has been added with the [deepaas-predict](https://github.com/indigo-dc/DEEPaaS/blob/master/deepaas/cmd/execute.py) command.

## Usage in AWS Batch via SCAR

Enter the [AWS Batch integration in SCAR](https://scar.readthedocs.io/en/latest/batch.html). This allows to delegate event-driven executions of jobs that do not fit in the AWS Lambda constraints into AWS Batch in order to be executed as containers out of the user-defined Docker images on Amazon EC2 instances.

For the example we are using the file: [file_example_WAV_1MG.wav](file_example_WAV_1MG.wav)

### Event driven invocation (using S3)

You can run a container out of this image on AWS Batch via [SCAR](https://github.com/grycap/scar) using the following procedure:

Create the Lambda function using the `scar-deepaas-audio.yaml` configuration file:

```sh
scar init -f scar-deepaas-audio.yaml
```

Launch the Lambda function uploading a file to the `s3://scar-deepaas/audio/input` folder in S3.

Take into consideration than the first invocation will take considerably longer than the subsequent ones, where the container will be cached.

### Processing the S3 output

When the function execution ends, the script used produces an output file with the prediction result and SCAR copies them to the used S3 bucket.

The file is created in the output folder: `s3://scar-deepaas/audio/output`.


In our case the output file is audio_output_admin_out_file_example_WAV_1MG.json:

```sh
[{'title': 'file_example_WAV_1MG.wav', 'labels': ['Music', 'Musical instrument', 'Sampler', 'Funny music', 'Guitar'], 'probabilities': [0.8079842329025269, 0.2382311075925827, 0.10627777129411697, 0.09718459844589233, 0.09593614190816879], 'labels_info': ['/m/04rlf', '/m/04szw', '/m/01v1d8', '/t/dd00032', '/m/0342h'], 'links': {'Google Images': ['https://www.google.es/search?tbm=isch&q=Music', 'https://www.google.es/search?tbm=isch&q=Musical+instrument', 'https://www.google.es/search?tbm=isch&q=Sampler', 'https://www.google.es/search?tbm=isch&q=Funny+music', 'https://www.google.es/search?tbm=isch&q=Guitar'], 'Wikipedia': ['https://en.wikipedia.org/wiki/Music', 'https://en.wikipedia.org/wiki/Musical_instrument', 'https://en.wikipedia.org/wiki/Sampler', 'https://en.wikipedia.org/wiki/Funny_music', 'https://en.wikipedia.org/wiki/Guitar']}}]
```

Don't forget to delete the function when you finish your testing:

```sh
scar rm -f scar-deepaas-audio.yaml
```