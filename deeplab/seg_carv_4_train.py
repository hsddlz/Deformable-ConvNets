# pylint: skip-file
import sys, os
import argparse
import mxnet as mx
import numpy as np
import logging

import seg_carv_7_init_from_cls
from symbols.irnext_v2_deeplab_v3_dcn_w_hypers import *
from seg_carv_1_data_loader import FileIter
from seg_carv_1_data_loader import BatchFileIter
from seg_carv_2_dicemetric import DiceMetric
from seg_carv_3_solver import Solver


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def main():
    
    devs = mx.cpu() if args.gpus is None or args.gpus is '' else [
        mx.gpu(int(i)) for i in args.gpus.split(',')]
    carvn_root = ''
    num_classes = 2
    cutoff = None if args.cutoff==0 else args.cutoff
    epochs = [74,30,10,5]
    if not os.path.exists(args.model_dir):
        os.mkdir(args.model_dir)
        
    if 'Deeplab' in args.model:
        
        print "arg.model name is : ", args.model
        cls_model_prefix = '-'.join(['CLS'] + args.model.split('-')[1:])
        
        deeplabnet = irnext_deeplab_dcn(**vars(args))
        deeplabsym = deeplabnet.get_seg_symbol()

        model_prefix = args.model
        load_prefix = cls_model_prefix
        lr = 0.001
        run_epochs = 20
        load_epoch = 10
    else:
        raise Exception("error")
        
    arg_names = deeplabsym.list_arguments()
    
    
    print('loading', load_prefix, load_epoch)
    print('lr', lr)
    print('model_prefix', model_prefix)
    print('running epochs', run_epochs)
    print('cutoff size', cutoff)
    
    args.batch_size = len(devs)
      
    if not args.retrain:
        ctx = mx.cpu()
        
        _ , deeplab_args, deeplab_auxs = mx.model.load_checkpoint(load_prefix, load_epoch)
        deeplab_args, deeplab_auxs = seg_carv_7_init_from_cls.init_from_irnext_cls(ctx, \
                                     deeplabsym, deeplab_args, deeplab_auxs)
            
            
            
    train_dataiter = BatchFileIter(
        path_imglist         = "../../carvana_train.lst",
        cut_off_size         = cutoff,
        rgb_mean             = (123.68, 116.779, 103.939),
        batch_size           = args.batch_size,
        )
    val_dataiter = BatchFileIter(
        path_imglist         = "../../carvana_val.lst",
        cut_off_size         = cutoff,
        rgb_mean             = (123.68, 116.779, 103.939),
        batch_size           = args.batch_size,
        )

    # learning rate
    kv = mx.kvstore.create('local')

    # create model
    model = mx.mod.Module(
        context       = devs,
        symbol        = deeplabsym,
        #label_names   = ['softmax_label', 'softmax2_label']
    )
    optimizer_params = {
            'learning_rate': lr,
            'momentum' : 0.90,
            'wd' : 0.0005 }
    _dice = DiceMetric()
    eval_metrics = [mx.metric.create(_dice)]
    initializer = mx.init.Xavier(rnd_type='gaussian', factor_type="in", magnitude=2)
    model.fit(train_dataiter,
        begin_epoch        = 0,
        num_epoch          = run_epochs,
        eval_data          = val_dataiter,
        eval_metric        = eval_metrics,
        kvstore            = kv,
        optimizer          = 'sgd',
        optimizer_params   = optimizer_params,
        initializer        = initializer,
        # arg_params         = deeplab_args,
        # aux_params         = deeplab_auxs,
        batch_end_callback = mx.callback.Speedometer(args.batch_size, 10),
        epoch_end_callback = mx.callback.do_checkpoint(model_prefix),
        allow_missing      = True)
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert IRNeXt to Deeplabv3 model.')
    
    
    parser.set_defaults(
        # network
        network          = 'irnext',
        num_layers       = 50,
        outfeature       = 1024,
        bottle_neck      = 1,
        expansion        = 1.0, 
        num_group        = 32,
        dilpat           = '', 
        irv2             = False, 
        deform           = 0, 
        taskmode         = 'SEG',
        seg_stride_mode  = '8x',
        # data
        num_classes      = 2,
        #num_examples     = 1281167,
        #image_shape      = '3,224,224',
        #lastout          = 7,
        #min_random_scale = 1.0 , # if input image has min size k, suggest to use
                              # 256.0/x, e.g. 0.533 for 480
        # train
        #num_epochs       = 80,
        #lr_step_epochs   = '30,50,70',
        dtype            = 'float32'
    )
    
    
    parser.add_argument('--model', default='DeeplabV3-ResNeXt-50L16X4D4XP',
        help='The type of DeeplabV3-ResNeXt model, e.g. DeeplabV3-ResNeXt-50L16X4D4XP, DeeplabV3-ResNeXt-50L96X4D1ov2XP')
    parser.add_argument('--model-dir', default='./model',
        help='directory to save model.')
    parser.add_argument('--cutoff', type=int, default=800,
        help='cutoff size.')
    parser.add_argument('--gpus', default='',
        help='gpus for use.')
    parser.add_argument('--retrain', action='store_true', default=True,
        help='true means continue training.')
    args = parser.parse_args()
    logging.info(args)
    
    main()

