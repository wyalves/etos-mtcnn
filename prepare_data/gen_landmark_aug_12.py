# coding: utf-8
import os
import random
from os.path import join, exists

import cv2
import numpy as np
import numpy.random as npr

from BBox_utils import getDataFromTxt, BBox
from Landmark_utils import rotate, flip
from utils import IoU




def GenerateData(ftxt,data_path,net,argument=False):
    '''

    :param ftxt: name/path of the text file that contains image path,
                bounding box, and landmarks

    :param output: path of the output dir
    :param net: one of the net in the cascaded networks
    :param argument: apply augmentation or not
    :return:  images and related landmarks
    '''
    if net == "PNet":
        size = 12
    elif net == "RNet":
        size = 24
    elif net == "ONet":
        size = 48
    else:
        print('Net type error')
        return
    image_id = 0
    #
    f = open(join(OUTPUT,"landmark_%s_aug.txt" %(size)),'w')
    #dstdir = "train_landmark_few"
    # get image path , bounding box, and landmarks from file 'ftxt'
    data = getDataFromTxt(ftxt,data_path=data_path)
    idx = 0
    #image_path bbox landmark(5*2)
    for (imgPath, bbox, landmarkGt) in data:
        #print imgPath
        F_imgs = []
        F_landmarks = []
        #print(imgPath)
        img = cv2.imread(imgPath)

        assert(img is not None)
        img_h,img_w,img_c = img.shape
        gt_box = np.array([bbox.left,bbox.top,bbox.right,bbox.bottom])
        #get sub-image from bbox
        f_face = img[bbox.top:bbox.bottom+1,bbox.left:bbox.right+1]
        # resize the gt image to specified size
        f_face = cv2.resize(f_face,(size,size))
        #initialize the landmark
        landmark = np.zeros((5, 2))

        #normalize land mark by dividing the width and height of the ground truth bounding box
        # landmakrGt is a list of tuples
        for index, one in enumerate(landmarkGt):
            # (( x - bbox.left)/ width of bounding box, (y - bbox.top)/ height of bounding box
            rv = ((one[0]-gt_box[0])/(gt_box[2]-gt_box[0]), (one[1]-gt_box[1])/(gt_box[3]-gt_box[1]))
            # put the normalized value into the new list landmark
            landmark[index] = rv
        
        F_imgs.append(f_face)
        F_landmarks.append(landmark.reshape(10))
        landmark = np.zeros((5, 2))        
        if argument:
            idx = idx + 1
            if idx % 100 == 0:
                print(idx, "images done")
            x1, y1, x2, y2 = gt_box
            #gt's width
            gt_w = x2 - x1 + 1
            #gt's height
            gt_h = y2 - y1 + 1        
            if max(gt_w, gt_h) < 40 or x1 < 0 or y1 < 0:
                continue
            #random shift
            for i in range(10):
                bbox_size = npr.randint(int(min(gt_w, gt_h) * 0.8), np.ceil(1.25 * max(gt_w, gt_h)))
                delta_x = npr.randint(-gt_w * 0.2, gt_w * 0.2)
                delta_y = npr.randint(-gt_h * 0.2, gt_h * 0.2)
                nx1 = int(max(x1+gt_w/2-bbox_size/2+delta_x,0))
                ny1 = int(max(y1+gt_h/2-bbox_size/2+delta_y,0))

                nx2 = nx1 + bbox_size
                ny2 = ny1 + bbox_size
                if nx2 > img_w or ny2 > img_h:
                    continue
                crop_box = np.array([nx1,ny1,nx2,ny2])


                cropped_im = img[ny1:ny2+1,nx1:nx2+1,:]
                resized_im = cv2.resize(cropped_im, (size, size))
                #cal iou
                iou = IoU(crop_box, np.expand_dims(gt_box,0))
                if iou > 0.65:
                    F_imgs.append(resized_im)
                    #normalize
                    for index, one in enumerate(landmarkGt):
                        rv = ((one[0]-nx1)/bbox_size, (one[1]-ny1)/bbox_size)
                        landmark[index] = rv
                    F_landmarks.append(landmark.reshape(10))
                    landmark = np.zeros((5, 2))
                    landmark_ = F_landmarks[-1].reshape(-1,2)
                    bbox = BBox([nx1,ny1,nx2,ny2])                    

                    #mirror                    
                    if random.choice([0,1]) > 0:
                        face_flipped, landmark_flipped = flip(resized_im, landmark_)
                        face_flipped = cv2.resize(face_flipped, (size, size))
                        #c*h*w
                        F_imgs.append(face_flipped)
                        F_landmarks.append(landmark_flipped.reshape(10))
                    #rotate
                    if random.choice([0,1]) > 0:
                        face_rotated_by_alpha, landmark_rotated = rotate(img, bbox, \
                                                                         bbox.reprojectLandmark(landmark_), 5)#逆时针旋转
                        #landmark_offset
                        landmark_rotated = bbox.projectLandmark(landmark_rotated)
                        face_rotated_by_alpha = cv2.resize(face_rotated_by_alpha, (size, size))
                        F_imgs.append(face_rotated_by_alpha)
                        F_landmarks.append(landmark_rotated.reshape(10))
                
                        #flip
                        face_flipped, landmark_flipped = flip(face_rotated_by_alpha, landmark_rotated)
                        face_flipped = cv2.resize(face_flipped, (size, size))
                        F_imgs.append(face_flipped)
                        F_landmarks.append(landmark_flipped.reshape(10))                
                    
                    #anti-clockwise rotation
                    if random.choice([0,1]) > 0: 
                        face_rotated_by_alpha, landmark_rotated = rotate(img, bbox, \
                                                                         bbox.reprojectLandmark(landmark_), -5)#顺时针旋转
                        landmark_rotated = bbox.projectLandmark(landmark_rotated)
                        face_rotated_by_alpha = cv2.resize(face_rotated_by_alpha, (size, size))
                        F_imgs.append(face_rotated_by_alpha)
                        F_landmarks.append(landmark_rotated.reshape(10))
                
                        face_flipped, landmark_flipped = flip(face_rotated_by_alpha, landmark_rotated)
                        face_flipped = cv2.resize(face_flipped, (size, size))
                        F_imgs.append(face_flipped)
                        F_landmarks.append(landmark_flipped.reshape(10)) 
                    
            F_imgs, F_landmarks = np.asarray(F_imgs), np.asarray(F_landmarks)
            #print F_imgs.shape
            #print F_landmarks.shape
            for i in range(len(F_imgs)):
                #if image_id % 100 == 0:

                    #print('image id : ', image_id)

                if np.sum(np.where(F_landmarks[i] <= 0, 1, 0)) > 0:
                    continue

                if np.sum(np.where(F_landmarks[i] >= 1, 1, 0)) > 0:
                    continue

                cv2.imwrite(join(dstdir,"%d.jpg" %(image_id)), F_imgs[i])
                landmarks = map(str,list(F_landmarks[i]))
                f.write(join(dstdir,"%d.jpg" %(image_id))+" -2 "+" ".join(landmarks)+"\n")
                image_id = image_id + 1
            
    #print F_imgs.shape
    #print F_landmarks.shape
    #F_imgs = processImage(F_imgs)
    #shuffle_in_unison_scary(F_imgs, F_landmarks)
    
    f.close()
    return F_imgs,F_landmarks

if __name__ == '__main__':
    dstdir = "../../DATA/12/train_PNet_landmark_aug"
    OUTPUT = '../../DATA/12'
    data_path = '../../DATA'
    if not exists(OUTPUT):
        os.mkdir(OUTPUT)
    if not exists(dstdir):
        os.mkdir(dstdir)
    assert (exists(dstdir) and exists(OUTPUT))
    # train data
    net = "PNet"
    #the file contains the names of all the landmark training data
    train_txt = "trainImageList.txt"
    imgs,landmarks = GenerateData(train_txt,data_path,net,argument=True )
    
   
