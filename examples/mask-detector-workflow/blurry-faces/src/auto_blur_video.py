# author: Asmaa Mirkhan ~ 2019

import os
import argparse
import cv2 as cv
from DetectorAPI import DetectorAPI

def blurBoxes(image, boxes):
    """
    Argument:
    image -- the image that will be edited as a matrix
    boxes -- list of boxes that will be blurred, each box must be int the format (x_top_left, y_top_left, x_bottom_right, y_bottom_right)

    Returns:
    image -- the blurred image as a matrix
    """

    for box in boxes:
        # unpack each box
        x1, y1, x2, y2 = [d for d in box]

        # crop the image due to the current box
        sub = image[y1:y2, x1:x2]

        # apply GaussianBlur on cropped area
        blur = cv.blur(sub, (25, 25))

        # paste blurred image on the original image
        image[y1:y2, x1:x2] = blur

    return image


def main(args):
    # assign model path and threshold
    model_path = args.model_path
    threshold = args.threshold

    # create detection object
    odapi = DetectorAPI(path_to_ckpt=model_path)

    # open video
    capture = cv.VideoCapture(args.input_video)

    # video width = capture.get(3)
    # video height = capture.get(4)
    # video fps = capture.get(5)

    if args.output_video:
        fourcc = cv.VideoWriter_fourcc(*'mp4v')
        output = cv.VideoWriter(args.output_video, fourcc,
                                20.0, (int(capture.get(3)), int(capture.get(4))))

    frame_counter = 0
    while True:
        # read frame by frame
        r, frame = capture.read()
        frame_counter += 1

        # the end of the video?
        if frame is None:
            break

        key = cv.waitKey(1)
        if key & 0xFF == ord('q'):
            break
        # real face detection
        boxes, scores, classes, num = odapi.processFrame(frame)

        # filter boxes due to threshold
        # boxes are in (x_top_left, y_top_left, x_bottom_right, y_bottom_right) format
        boxes = [boxes[i] for i in range(0, num) if scores[i] > threshold]

        # apply blurring
        frame = blurBoxes(frame, boxes)

        # show image
        cv.imshow('blurred', frame)

    # if image will be saved then save it
        if args.output_video:
            output.write(frame)
            print('Blurred video has been saved successfully at',
                  args.output_video, 'path')

    # when any key has been pressed then close window and stop the program

    cv.destroyAllWindows()


if __name__ == "__main__":
    # creating argument parser
    parser = argparse.ArgumentParser(description='Image blurring parameters')

    # adding arguments
    parser.add_argument('-i',
                        '--input_video',
                        help='Path to your video',
                        type=str,
                        required=True)
    parser.add_argument('-m',
                        '--model_path',
                        help='Path to .pb model',
                        type=str,
                        required=True)
    parser.add_argument('-o',
                        '--output_video',
                        help='Output file path',
                        type=str)
    parser.add_argument('-t',
                        '--threshold',
                        help='Face detection confidence',
                        default=0.7,
                        type=float)
    args = parser.parse_args()
    print(args)
    # if input image path is invalid then stop
    assert os.path.isfile(args.input_video), 'Invalid input file'

    # if output directory is invalid then stop
    if args.output_video:
        assert os.path.isdir(os.path.dirname(
            args.output_video)), 'No such directory'

    main(args)
