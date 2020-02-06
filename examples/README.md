# Usage Examples of SCAR

This directory includes different use cases of applications packaged as Docker images that can be easily executed on AWS Lambda using SCAR:

* [AWS CLI](https://aws.amazon.com/cli/), to execute shell-scripts using this tool.
* [Cowsay](https://en.wikipedia.org/wiki/Cowsay) and [Fortune](https://en.wikipedia.org/wiki/Fortune_(Unix)), just for silly testing.
* [Darknet](https://pjreddie.com/darknet) is an open source neural network framework written in C and CUDA. For the example we will be using the library 'You only look once' [YOLO](https://pjreddie.com/darknet/yolo/) which is  is a state-of-the-art, real-time object detection system
* [Elixir](https://elixir-lang.org/), to proof that you can run code in programming languages other than those supported by AWS Lambda.
* [Erlang](https://www.erlang.org/), to proof that you can run code in programming languages other than those supported by AWS Lambda.
* [FFmpeg](https://ffmpeg.org/), a tool to transcode and manipulate videos.
* [ImageMagick](https://www.imagemagick.org), a tool to manipulate images.
* [MrBayes](http://mrbayes.sourceforge.net/), a scientific application for bayesian inference of Phylogeny.
* [R](https://www.r-project.org/), a free software environment for statistical computing and graphics.
* [Ruby](https://www.ruby-lang.org), a dynamic, open source programming language with a focus on simplicity and productivity.
* [Theano](http://deeplearning.net/software/theano/), a Python library that allows you to define, optimize, and evaluate mathematical expressions involving multi-dimensional arrays efficiently.

There are also examples that combine AWS Lambda and AWS Batch in order to offer event-driven file-processing computing for applications with requirements that do not fit in the AWS Lambda constraints:

* video-process: an application to perform object recognition from videos using AWS Batch and AWS Lambda.
* plant-classification: an application to classify plants using Lasagne/Theano.
* av-workflow: a workflow that combines [FFmpeg](https://ffmpeg.org/), [YOLOv3](https://pjreddie.com/darknet/yolo/) and [audio2srt](https://gitlab.com/RunasSudo/audio2srt) to perform automatic subtitle generation and GPU-based video object recognition.

Are you using SCAR for another application? Let us know by creating an issue.
