import os
import argparse
import logging
logging.basicConfig(level=logging.DEBUG)
from common import find_mxnet, data, fit
from common.util import download_file
import mxnet as mx
from symbols.irnext_v2_deeplab_v3_dcn_w_hypers import *
import runs_CAIScene.scene_init_from_cls


if __name__ == '__main__':
    # parse args
    parser = argparse.ArgumentParser(description="train imagenet1k",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    fit.add_fit_args(parser)
    data.add_data_args(parser)
    data.add_data_aug_args(parser)
    # use a large aug level
    data.set_data_aug_level(parser, 3)
    parser.set_defaults(
        # network
        network          = 'irnext',
        num_layers       = 152,
        outfeature       = 2048,
        bottle_neck      = 1,
        expansion        = 4, 
        num_group        = 1,
        dilpat           = '', 
        irv2             = False, 
        deform           = 1,
        sqex             = 1,
        ratt             = 0,
        block567         = 0,
        lmar             = 0,
        lmarbeta         = 1,
        lmarbetamin      = 0,
        lmarscale        = 1,
        # data
        num_classes      = 80,
        num_examples     = 53878,
        image_shape      = '3,224,224',
        lastout          = 7,
        min_random_scale = 1.0 , # if input image has min size k, suggest to use
                              # 256.0/x, e.g. 0.533 for 480
        # train
        num_epochs       = 100,
        lr               = 0.01,
        lr_step_epochs   = '20,40',
        dtype            = 'float32',
        
        # load
        load_ft_epoch       = 0,
        model_ft_prefix     = 'CLS-ResNeXt-152L64X1D4XP'
        
    )
    args = parser.parse_args()

    # load network
    #from importlib import import_module
    #net = import_module('symbols.'+args.network)
    # sym = net.get_symbol(**vars(args))
    
    net = irnext_deeplab_dcn(**vars(args))
    sym = net.get_cls_symbol()

    # Init Parameters
    ctx = mx.cpu()
        
    _ , deeplab_args, deeplab_auxs = mx.model.load_checkpoint(args.model_ft_prefix, args.load_ft_epoch)
        
        
    data_shape_dict = {'data': (args.batch_size, 3, 224, 224), 
                           'softmax_label': (args.batch_size,)}

        
    deeplab_args, deeplab_auxs = runs_CAIScene.scene_init_from_cls.init_from_irnext_cls(ctx, \
                            sym, deeplab_args, deeplab_auxs, data_shape_dict, block567=args.block567)
    
    # train
    
    #args.arg_params         = deeplab_args
    #args.aux_params         = deeplab_auxs
    fit.fit(args, sym, data.get_rec_iter, arg_params=deeplab_args,aux_params=deeplab_auxs)

