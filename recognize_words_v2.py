# -*- coding: utf-8 -*-
"""
Created on Thu Nov 24 15:41:47 2016

@author: sgnosh
"""

# -*- coding: utf-8 -*-
"""
Created on Tue Aug 16 18:52:31 2016


@author: sgnosh
""

""
Sampling script for attention models

Works on CPU with support for multi-process
"""
import argparse
import numpy
import cPickle as pkl
import pandas as pd
import time
import math 
import numpy as np


import sys
#here#
import os


#
from set_param_paths import set_param_paths

pathDict = set_param_paths()
sys.path.insert(0, pathDict['caffe_root'] + 'python')
import caffe

from skimage.transform import resize as resize
from skimage import io as imio

from capgen import build_sampler, gen_sample, \
                   load_params, \
                   init_params, \
                  init_tparams


#from multiprocessing import Process, Queue
def gencap(cc0,f_init,f_next,tparams,trng,options,k,normalize):
        sample, score = gen_sample(tparams, f_init, f_next, cc0, options,
                                   trng=trng, k=k, maxlen=200, stochastic=False,alpha=0.0)
        # adjust for length bias
        if normalize:
            lengths = numpy.array([len(s) for s in sample])
            score = score / lengths
        sidx = numpy.argsort(score)
        return [(sample[i],score[i]) for i in sidx]
    #seq = _gencap(context)

    #return (idx, seq)
def gen_model(model, options, k, normalize, word_idict, sampling):
    import theano
    from theano import tensor
    from theano.sandbox.rng_mrg import MRG_RandomStreams as RandomStreams

    trng = RandomStreams(1234)

   # DICTIONARY = "lexicon.txt"
    # this is zero indicate we are not using dropout in the graph
    use_noise = theano.shared(numpy.float32(0.), name='use_noise')

    # get the parameters
    params = init_params(options)
    params = load_params(model, params)
    tparams = init_tparams(params)

    # build the sampling computational graph
    # see capgen.py for more detailed explanations
    f_init, f_next = build_sampler(tparams, options, use_noise, trng, sampling=sampling)


    return (f_init,f_next,tparams,trng)



def set_up_caffe(protoFile,modelFile,batchSize,useCPU):
    #Setup
    #caffe_root = '/home/sgnosh/caffe/'
#    sys.path.insert(0, caffe_root + 'python')
#    import caffe
    print 'Start Setup'
   
    mjLayoutFilename = protoFile #'models/synthText/dictnet_vgg_deploy.prototxt'
    mjModelFile = modelFile #'models/synthText/dictnet_vgg.caffemodel'
 
    if useCPU:
        caffe.set_mode_cpu()
    else:
        caffe.set_device(0)
        caffe.set_mode_gpu()
    #caffe.set_mode_gpu([0])
#    caffe.set_mode_cpu()
#    #caffe.set_device(0)
    net = caffe.Net(mjLayoutFilename,mjModelFile,caffe.TEST)

## input preprocessing: 'data' is the name of the input blob == net.inputs[0]
    transformer = caffe.io.Transformer({'data': net.blobs['data'].data.shape})
    net.blobs['data'].reshape(batchSize, 1, 32, 100)
    return net,transformer

def read_image(imagePath,filename):
   # for filename in os.listdir(imagePath):

   print imagePath+filename
   img =imio.imread(imagePath+filename)
   if len(img.shape) == 3 and img.shape[2] == 3:
       img =np.around(np.dot(img[...,:3], [0.2989, 0.5870, 0.1140]))
   img = np.array(img,dtype=np.uint8)
   img = resize(img, (32,100), order=1)
   img = np.array(img,dtype=np.float32) # convert to single precision
   img = (img -np.mean(img)) / ( (np.std(img) + 0.0001)/128 )
   return img
            #net.blobs['data'].data[...] = transformer.preproce931 18 45 31ss('data', img)

# return feature of one batch
    #input: img nd array
    #input : net caffe net object
    #input : transformer caffe transformer object
def feature_extractor(img,net,transformer):
    #net.blobs['data'].data[...] = transformer.preprocess('data', img)
            #net.blobs['data'].data[...] = transformer.preprocess('data', img)
    out = net.forward()
 
    feat = net.blobs['conv4'].data
 
    reshapeFeat = np.swapaxes(feat,1,3)
    reshapeFeat2 = np.reshape(reshapeFeat,(feat.shape[0],-1))
    return reshapeFeat2
def main(saveto, k=5, normalize=False, zero_pad=False,sampling=False, pkl_name=None):

#def main(saveto, k=10, normalize=False, zero_pad=False,sampling=False, pkl_name=None):
    # load model model_options

    # set paths parameters

    # setting up caffe here ---euracat
    batchSize= int(pathDict['batchSize'])
    net,transformer =set_up_caffe(pathDict['protoFile'],pathDict['modelFileCaffe'],batchSize,int(pathDict['useCPU']))

    if pathDict['paramFile'] is None:
        paramFile = pathDict['modelFileLSTM'].replace('.npz','.pkl')
      
    else:
        paramFile = pathDict['paramFile']
    with open('%s'% paramFile, 'rb') as f:
        options = pkl.load(f)


    with open(pathDict['dictFile'], 'rb') as f:
        worddict = pkl.load(f)
    word_idict = dict()
   
    for kk, vv in worddict.iteritems():
        word_idict[vv] = kk
      
    word_idict[0] = '<eos>'
    word_idict[1] = 'UNK'
    # generate models
    f_init,f_next,tparams,trng = gen_model(pathDict['modelFileLSTM'], options, k, normalize, word_idict, sampling)
    # generates words using dictionary
    def _seqs2words(caps):
            #print caps
            capsw = []
            for cc in caps:
                capW = []
                for cc0 in cc:
                    ww=[]
                    for w in cc0:
                        if w == 0:
                            break
                        ww.append(word_idict[w])
                    capW.append(''.join(ww))
                capsw.append(' '.join(capW))
               
            return capsw



    img_names = os.listdir(pathDict['image_path'])
    imgs = [read_image(pathDict['image_path'],filename) for filename in img_names]
    nProposals = len(imgs)
    
    caps = [None] * nProposals
    probs = [None] * nProposals
  

 


     # for each batch do the folmainlowinng

    #imgs = np.array(imgs)
    #imgs = imgs.reshape(batchSize,1,32,100)
    startime = time.clock()

    for start in range(0,nProposals,batchSize):
        for idx in range(start,min(start+batchSize,nProposals)):
            net.blobs['data'].data[idx-start] = transformer.preprocess('data', imgs[idx])
        #ctx = feature_extractor(imgs,net,transformer)
        out = net.forward()
        feat = net.blobs['conv4'].data
    #reshapeFeat = np.swapaxes(feat,0,2)
    #reshapeFeat2 = np.reshape(reshapeFeat,(1,-1))
        reshapeFeat = np.swapaxes(feat,1,3)
        ctx = np.reshape(reshapeFeat,(feat.shape[0],-1))
      
        # for last iteration discard the last rows
        if start+batchSize > nProposals:
            ctx = ctx[0:nProposals-start,:]
         
        for idx in range(ctx.shape[0]):
            # calculate feature for every proposal here

            #imName = '=sample1.jpg'
            #st = time.clock()
           # img = read_image(image_path,image_name,bbox[idx,:-1])


            cc = (ctx[idx]).reshape([4*13,512]) # as per the input feature size
        
            if zero_pad:
                        cc0 = numpy.zeros((cc.shape[0]+1, cc.shape[1])).astype('float32')
                        cc0[:-1,:] = cc
            else:
                        cc0 = cc
            resp=gencap(cc0,f_init,f_next,tparams,trng,options,k,normalize)
            
            # if more than one output needed change here
            resp_cap=[ r for (r,p) in resp]
            prob=[ p for (r,p) in resp]
           ## my code start here   
           #print('resp_cap')
           #print resp_cap
           #print('prob_before_caps')
           #print prob 
            z  = prob 
            def softmax(x):
                scoreMatExp = np.exp(x- np.max(x))
                return scoreMatExp / scoreMatExp.sum(0)
            #print(softmax(z))  
            #prob1 = softmax[::-1]
            a = softmax(z)
            prob1 =  a[::-1]
            #print prob1
            prob1 =  " ".join(str(x) for x in prob1)
            print prob1 
            caps[start+idx] = resp_cap
            probs[start+idx] =prob
            
           #end = time.clock()
            #print end-st
    #print caps
    textResult = _seqs2words(caps)
    
    results =np.column_stack([img_names,textResult])

    #print results 
#     if saveto is None:
#        res = open(image_name.replace('_img.jpg','_res.txt','w'))
#    else:
#        res = open(saveto,'w')
#    for i,x in enumerate(textResult):
#        res.write(bbox[i]+x+'\n')
#    res.close()
    #print results
    np.savetxt(saveto,results,fmt='%s')

    #np.savetxt(saveto,results1,fmt='%s')
    #np.savetxt(image_name.replace('_img.jpg','_res.txt'),results,fmt='%s,%s,%s,%s,%s,%s')
    end = time.clock()
    print end-startime



if __name__ == "__main__":
    parser = argparse.ArgumentParser()

   # parser.add_argument('-image_name', type=str,default = '46_img.jpg')

    parser.add_argument('-saveto', type=str,default='result.txt')

    args = parser.parse_args()
    parser.add_argument('-k', type=int,default=5)
 

    args = parser.parse_args()

    main(args.saveto,args.k)
    #print status
#synthText_deterministic_model.exp9.npz_epoch_10

