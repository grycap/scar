#! /bin/bash

cat > classify_image.py << EOF
import os
import sys
import json
import argparse

# Set matplotlib non-interactive backend to work in a container
import matplotlib
matplotlib.use('agg')

import numpy as np
import matplotlib.pylab as plt
from PIL import Image

from plant_classification.my_utils import single_prediction
from plant_classification.model_utils import load_model

def plot_image(filename, pred_lab, pred_prob, true_lab=None, output=None):
    """
    Display image and predicted label in matplotlib plot.

    Parameters
    ----------
    filename : str
        Image path
    pred_lab : numpy array
        Top5 prediction labels
    pred_prob : numpy array
        Top 5 prediction probabilities
    True_lab : str, None, optional
        True label
    output : None, output-file
        If None displays image + predicted labels in matplotlib plot.
        If False displays predicted labels in command line.

    """
    pred_tmp = ['{}.  {} | {:.0f} %'.format(str(i+1), p, pred_prob[i]*100) for i, p in enumerate(pred_lab)]
    text = r''
    if true_lab is not None:
        text += 'True label:\n\n     {}  \n\n'.format(true_lab)
    text += 'Predicted labels: \n\n    ' + '\n    '.join(pred_tmp)
    im = Image.open(filename)
    arr = np.asarray(im)
    fig = plt.figure(figsize=(20, 12))
    ax1 = fig.add_axes((.1, .1, .5, 0.9))
    ax1.imshow(arr)
    ax1.set_xticks([]), ax1.set_yticks([])
    ax1.set_xticklabels([]), ax1.set_yticklabels([])
    t = fig.text(.7, .5, text, fontsize=20)
    t.set_bbox(dict(color='white', alpha=0.5, edgecolor='black'))
    if output == None:
        plt.show()
    else:
        plt.savefig(output)

# Parse the options
parser = argparse.ArgumentParser()
parser.add_argument("FILE")
parser.add_argument("-o", "--output", help="Save the result to a local file.")
args = parser.parse_args()

#homedir = (os.path.dirname(os.path.realpath(__file__)))
homedir = '/srv/plant-classification-theano'

metadata_binomial = np.genfromtxt(os.path.join(homedir, 'data', 'data_splits', 'synsets.txt'), dtype='str', delimiter='/n')
modelname = 'resnet50_6182classes_100epochs'

# Load training info
info_file = os.path.join(homedir, 'plant_classification', 'training_info', modelname + '.json')
with open(info_file) as datafile:
    train_info = json.load(datafile)
mean_RGB = train_info['augmentation_params']['mean_RGB']
output_dim = train_info['training_params']['output_dim']

# Load net weights
test_func = load_model(os.path.join(homedir, 'plant_classification', 'training_weights', modelname + '.npz'), output_dim=output_dim)

# Predict single local image
im_path = [args.FILE]
pred_lab, pred_prob = single_prediction(test_func, im_list=im_path, aug_params={'mean_RGB': mean_RGB})
plot_image(im_path[0], metadata_binomial[pred_lab], pred_prob, output=args.output)
EOF


echo "SCRIPT: Invoked classify_image.py. File available in $INPUT_FILE_PATH."
FILE_NAME=`basename $INPUT_FILE_PATH`
OUTPUT_FILE=$TMP_OUTPUT_DIR/$FILE_NAME
echo "OUTPUT FILE: $OUTPUT_FILE"
python2 `pwd`/classify_image.py $INPUT_FILE_PATH -o $OUTPUT_FILE


