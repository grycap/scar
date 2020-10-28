# author: Asmaa Mirkhan ~ 2019

import os
import argparse
import cv2 as cv


def blurBoxes(image, boxes):
    """
    Argument:
    image -- the image that will be edited as a matrix
    boxes -- list of boxes that will be blurred, each box must be int the format (x_top_left, y_top_left, width, height)
    
    Returns:
    image -- the blurred image as a matrix
    """
    
    for box in boxes:
        # unpack each box
        x,y,w,h = [d for d in box]
        
        # crop the image due to the current box
        sub = image[y:y+h, x:x+w]
        
        # apply GaussianBlur on cropped area
        blur = cv.GaussianBlur(sub, (23,23), 30)
        
        # paste blurred image on the original image
        image[y:y+h, x:x+w] = blur
        
    return image


def main(args):
    # open the image
    image = cv.imread(args.input_image)
    
    # create a copy and do temp operations without affecting the original image
    temp_image = image.copy()
    
    # an array to store selected regions coordinates
    ROIs = []
    
    # keep getting ROIs until pressing 'q'
    while True:
        # get ROI cv.selectROI(window_name, image_matrix, selecting_start_point) 
        box = cv.selectROI('blur', temp_image, fromCenter=False)
        
        # add selected box to box list
        ROIs.append(box)
        
        # draw a rectangle on selected ROI
        cv.rectangle(temp_image, (box[0],box[1]), (box[0]+box[2], box[1]+box[3]), (0,255,0), 3)
        print('ROI is saved, press q to stop capturing, press any other key to select other ROI')
        
        # if 'q' is pressed then break
        key = cv.waitKey(0)
        if key & 0xFF == ord('q'):
            break
    
    # apply blurring
    image = blurBoxes(image, ROIs)
    
    # if image will be saved then save it
    if args.output_image:
        cv.imwrite(args.output_image,image)
    cv.imshow('blurred',image)
    cv.waitKey(0)
    
    

if __name__ == "__main__":
    # creating argument parser
    parser = argparse.ArgumentParser(description='Image blurring parameters')
    
    # adding arguments
    parser.add_argument('-i', '--input_image',
                        help='Path to your image', type=str, required=True)
    parser.add_argument('-o', '--output_image',
                        help='Output file path', type=str)
    args = parser.parse_args()
    
    # if input image path is invalid then stop
    assert os.path.isfile(args.input_image), 'Invalid input file'
    
    # if output directory is invalid then stop
    if args.output_image:
        assert os.path.isdir(os.path.dirname(
            args.output_image)), 'No such directory'

    main(args)
