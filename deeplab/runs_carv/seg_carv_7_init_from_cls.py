# pylint: skip-file
import mxnet as mx
import numpy as np
import sys
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# make a bilinear interpolation kernel, return a numpy.ndarray
def upsample_filt(size):
    factor = (size + 1) // 2
    if size % 2 == 1:
        center = factor - 1.0
    else:
        center = factor - 0.5
    og = np.ogrid[:size, :size]
    return (1 - abs(og[0] - center) / factor) * \
           (1 - abs(og[1] - center) / factor)



def init_from_irnext_cls(ctx, irnext_cls_symbol, irnext_cls_args, irnext_cls_auxs, data_shape_dict, block567=False):
    
    deeplab_args = irnext_cls_args.copy()
    deeplab_auxs = irnext_cls_args.copy()
    
    arg_name = irnext_cls_symbol.list_arguments()
    aux_name = irnext_cls_symbol.list_auxiliary_states()
    arg_shape, _, aux_shape = irnext_cls_symbol.infer_shape(**data_shape_dict)
    arg_shape_dict = dict(zip(arg_name, arg_shape))
    aux_shape_dict = dict(zip(aux_name, aux_shape))

    for k,v in deeplab_args.items():
        if(v.context != ctx):
            deeplab_args[k] = mx.nd.zeros(v.shape, ctx)
            v.copyto(deeplab_args[k])
        if k.startswith('fc6_'):
            if k.endswith('_weight'):
                print('initializing',k)
                deeplab_args[k] = mx.random.normal(0, 0.01, shape=v)
            elif k.endswith('_bias'):
                print('initializing',k)
                deeplab_args[k] = mx.nd.zeros(shape=v)
        if block567:
            if k.startswith('stage'):
                stage_id = int(k[5])
            if stage_id>4:
                rk = "stage4"+k[6:]
                if rk in irnext_cls_args:
                    print('initializing', k, rk)
                    if arg_shape_dict[rk]==v:
                        irnext_cls_args[k] = irnext_cls_args[rk].copy()
                    else:
                        if k.endswith('_beta'):
                            irnext_cls_args[k] = mx.nd.zeros(shape=v)
                        elif k.endswith('_gamma'):
                            irnext_cls_args[k] = mx.nd.random_uniform(shape=v)
                        else:
                            irnext_cls_args[k] = mx.random.normal(0, 0.01, shape=v)
        if 'se' in k:
            deeplab_args[k] = mx.nd.zeros(shape=v)
        
        
        
    for k,v in deeplab_auxs.items():
        if(v.context != ctx):
            deeplab_auxs[k] = mx.nd.zeros(v.shape, ctx)
            v.copyto(deeplab_auxs[k])
        if block567:
            if k.startswith('stage'):
                stage_id = int(k[5])
            if stage_id>4:
                rk = "stage4"+k[6:]
                if rk in irnext_cls_auxs:
                    print('initializing', k, rk)
                    if aux_shape_dict[rk]==v:
                        irnext_cls_auxs[k] = irnext_cls_auxs[rk].copy()
                    else:
                        if k.endswith('_beta'):
                            irnext_cls_auxs[k] = mx.nd.zeros(shape=v)
                        elif k.endswith('_gamma'):
                            irnext_cls_auxs[k] = mx.nd.random_uniform(shape=v)
                        else:
                            irnext_cls_auxs[k] = mx.random.normal(0, 0.01, shape=v)
   
    data_shape=(1,3,1024,1024)
    arg_names = irnext_cls_symbol.list_arguments()
    print arg_names
    print "Step"
    arg_shapes, _, _ = irnext_cls_symbol.infer_shape(data=data_shape)
    print arg_shapes
    rest_params = dict([(x[0], mx.nd.zeros(x[1], ctx)) for x in zip(arg_names, arg_shapes)
            if x[0] in ['score_weight', 'score_bias', 'score_pool4_weight', 'score_pool4_bias', \
                        'score_pool3_weight', 'score_pool3_bias', 'score_0_weight', 'score_0_bias', \
                        'score_1_weight', 'score_1_bias', 'score_2_weight', 'score_2_bias', \
                        'score_3_weight', 'score_3_bias']])
    deeplab_args.update(rest_params)
    print "Step"
    deconv_params = dict([(x[0], x[1]) for x in zip(arg_names, arg_shapes)
            if x[0] in ["upsampling_weight"]])
    
    for k, v in deconv_params.items():
        filt = upsample_filt(v[3])
        initw = np.zeros(v)
        initw[range(v[0]), range(v[1]), :, :] = filt  # becareful here is the slice assing
        deeplab_args[k] = mx.nd.array(initw, ctx)
    return deeplab_args, deeplab_auxs
    
'''

def init_from_vgg16(ctx, fcnxs_symbol, vgg16fc_args, vgg16fc_auxs):
    fcnxs_args = vgg16fc_args.copy()
    fcnxs_auxs = vgg16fc_auxs.copy()
    for k,v in fcnxs_args.items():
        if(v.context != ctx):
            fcnxs_args[k] = mx.nd.zeros(v.shape, ctx)
            v.copyto(fcnxs_args[k])
    for k,v in fcnxs_auxs.items():
        if(v.context != ctx):
            fcnxs_auxs[k] = mx.nd.zeros(v.shape, ctx)
            v.copyto(fcnxs_auxs[k])
    data_shape=(1,3,500,500)
    arg_names = fcnxs_symbol.list_arguments()
    arg_shapes, _, _ = fcnxs_symbol.infer_shape(data=data_shape)
    rest_params = dict([(x[0], mx.nd.zeros(x[1], ctx)) for x in zip(arg_names, arg_shapes)
            if x[0] in ['score_weight', 'score_bias', 'score_pool4_weight', 'score_pool4_bias', \
                        'score_pool3_weight', 'score_pool3_bias']])
    fcnxs_args.update(rest_params)
    deconv_params = dict([(x[0], x[1]) for x in zip(arg_names, arg_shapes)
            if x[0] in ["bigscore_weight", 'score2_weight', 'score4_weight']])
    for k, v in deconv_params.items():
        filt = upsample_filt(v[3])
        initw = np.zeros(v)
        initw[range(v[0]), range(v[1]), :, :] = filt  # becareful here is the slice assing
        fcnxs_args[k] = mx.nd.array(initw, ctx)
    return fcnxs_args, fcnxs_auxs

def init_from_fcnxs(ctx, fcnxs_symbol, fcnxs_args_from, fcnxs_auxs_from):
    """ use zero initialization for better convergence, because it tends to oputut 0,
    and the label 0 stands for background, which may occupy most size of one image.
    """
    fcnxs_args = fcnxs_args_from.copy()
    fcnxs_auxs = fcnxs_auxs_from.copy()
    for k,v in fcnxs_args.items():
        if(v.context != ctx):
            fcnxs_args[k] = mx.nd.zeros(v.shape, ctx)
            v.copyto(fcnxs_args[k])
    for k,v in fcnxs_auxs.items():
        if(v.context != ctx):
            fcnxs_auxs[k] = mx.nd.zeros(v.shape, ctx)
            v.copyto(fcnxs_auxs[k])
    data_shape=(1,3,500,500)
    arg_names = fcnxs_symbol.list_arguments()
    arg_shapes, _, _ = fcnxs_symbol.infer_shape(data=data_shape)
    rest_params = {}
    deconv_params = {}
    # this is fcn8s init from fcn16s
    if 'score_pool3_weight' in arg_names:
        rest_params = dict([(x[0], mx.nd.zeros(x[1], ctx)) for x in zip(arg_names, arg_shapes)
            if x[0] in ['score_pool3_bias', 'score_pool3_weight']])
        deconv_params = dict([(x[0], x[1]) for x in zip(arg_names, arg_shapes) if x[0] \
            in ["bigscore_weight", 'score4_weight']])
    # this is fcn16s init from fcn32s
    elif 'score_pool4_weight' in arg_names:
        rest_params = dict([(x[0], mx.nd.zeros(x[1], ctx)) for x in zip(arg_names, arg_shapes)
            if x[0] in ['score_pool4_weight', 'score_pool4_bias']])
        deconv_params = dict([(x[0], x[1]) for x in zip(arg_names, arg_shapes) if x[0] \
            in ["bigscore_weight", 'score2_weight']])
    # this is fcn32s init
    else:
        logging.error("you are init the fcn32s model, so you should use init_from_vgg16()")
        sys.exit()
    fcnxs_args.update(rest_params)
    for k, v in deconv_params.items():
        filt = upsample_filt(v[3])
        initw = np.zeros(v)
        initw[range(v[0]), range(v[1]), :, :] = filt  # becareful here is the slice assing
        fcnxs_args[k] = mx.nd.array(initw, ctx)
    return fcnxs_args, fcnxs_auxs

'''