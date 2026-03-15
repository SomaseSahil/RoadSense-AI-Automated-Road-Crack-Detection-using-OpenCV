# importing necessary libraries
import numpy as np
import cv2
from matplotlib import pyplot as plt

import os
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def process_cracks(image_path):
    # read a cracked sample image
    img = cv2.imread(image_path)
    if img is None:
        return None, 0, 0

    # Convert into gray scale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Image processing ( smoothing )
    # Averaging
    blur = cv2.blur(gray,(3,3))

    # Apply logarithmic transform
    img_log = (np.log(blur+1)/(np.log(1+np.max(blur))))*255

    # Specify the data type
    img_log = np.array(img_log,dtype=np.uint8)

    # Image smoothing: bilateral filter
    bilateral = cv2.bilateralFilter(img_log, 5, 75, 75)

    # Canny Edge Detection
    edges = cv2.Canny(bilateral,50,150)

    # Morphological Closing Operator
    kernel = np.ones((5,5),np.uint8)
    closing = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    # Calculate Crack Percentage based on the closing image (white pixels are cracks)
    num_crack_pixels = cv2.countNonZero(closing)
    total_pixels = closing.shape[0] * closing.shape[1]
    crack_percentage = (num_crack_pixels / total_pixels) * 100

    # Extract contours from the closed mask
    contours, hierarchy = cv2.findContours(closing, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Prepare output image (original color image)
    featuredImg = img.copy()

    crack_count = 0

    # Iterate through all isolated contours (cracks)
    for cnt in contours:
        area = cv2.contourArea(cnt)
        # Filter out tiny noise contours
        if area > 20:
            # Draw exact crack shape in Solid Red directly onto the color image
            cv2.drawContours(featuredImg, [cnt], -1, (0, 0, 255), 2)
            crack_count += 1
            
            # For major structural failures, draw a bounding box
            if area > 100:
                x, y, w, h = cv2.boundingRect(cnt)
                # Draw Neon Green bounding box
                cv2.rectangle(featuredImg, (x, y), (x+w, y+h), (0, 255, 0), 2)

    # Generate a unique output filename
    filename = f"out_{int(time.time())}.jpg"
    output_path = os.path.join(BASE_DIR, 'output', filename)
    
    # Ensure Output-Set exists
    if not os.path.exists(os.path.join(BASE_DIR, 'output')):
        os.makedirs(os.path.join(BASE_DIR, 'output'))
        
    cv2.imwrite(output_path, featuredImg)
    
    return filename, crack_percentage, crack_count

if __name__ == '__main__':
    # Default behavior for manual testing
    res_name, pct, count = process_cracks('dataset/Cracked_07.jpg')
    print(f"Crack percentage: {pct:.2f}%")
    print(f"Crack count: {count}")
    
    if res_name is not None:
        # Original plot code for manual run
        img = cv2.imread('dataset/Cracked_07.jpg')
        featuredImg = cv2.imread(os.path.join('output', res_name))
        plt.subplot(121),plt.imshow(img)
        plt.title('Original'),plt.xticks([]), plt.yticks([])
        plt.subplot(122),plt.imshow(featuredImg,cmap='gray')
        plt.title('Output Image'),plt.xticks([]), plt.yticks([])
        plt.show()
    else:
        print("Test image not found. Please make sure 'dataset/Cracked_07.jpg' exists!")
