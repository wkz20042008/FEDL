import h5py
import matplotlib.pyplot as plt
import numpy as np
import argparse
import importlib
import random
import os
import tensorflow.compat.v1 as tf
tf.disable_v2_behavior() 
from flearn.utils.plot_utils import *
from flearn.utils.model_utils import read_data
import matplotlib
matplotlib.use('Agg')

# GLOBAL PARAMETERS
OPTIMIZERS = ['fedavg', 'fedprox', 'fedsgd', 'fedfedl']

DATASETS = ['nist', 'mnist', 'fashion_mnist', 'linear_synthetic']  # NIST is EMNIST in the paper

MODEL_PARAMS = {
    'sent140.bag_dnn': (2,),  # num_classes
    'sent140.stacked_lstm': (25, 2, 100),  # seq_len, num_classes, num_hidden
    # seq_len, num_classes, num_hidden
    'sent140.stacked_lstm_no_embeddings': (25, 2, 100),
    # num_classes, should be changed to 62 when using EMNIST
    'nist.mclr': (62,),
    'nist.cnn': (62,),
    'mnist.mclr': (10,),  # num_classes
    'mnist.cnn': (10,),  # num_classes
    'fashion_mnist.mclr': (10,),
    'fashion_mnist.cnn': (10,),
    'linear_synthetic.linear': (1,),  # seq_len, emb_dim, num_hidden
    'synthetic.mclr': (10, )  # num_classes
}


def read_options(num_users=5, loc_ep=10, Numb_Glob_Iters=100, lamb=0, learning_rate=0.01,hyper_learning_rate= 0.01, alg='fedprox', weight=True, batch_size=0, times = 10, rho = 0, dataset="mnist"):
    ''' Parse command line arguments or load defaults '''
    parser = argparse.ArgumentParser()

    parser.add_argument('--optimizer',
                        help='name of optimizer;',
                        type=str,
                        choices=OPTIMIZERS,
                        default=alg)  # fedavg, fedprox
    parser.add_argument('--dataset',
                        help='name of dataset;',
                        type=str,
                        choices=DATASETS,
                        default=dataset)
    parser.add_argument('--model',
                        help='name of model;',
                        type=str,
                        default='linear.py')  # 'stacked_lstm.py'
    parser.add_argument('--num_rounds',
                        help='number of rounds to simulate;',
                        type=int,
                        default=Numb_Glob_Iters)
    parser.add_argument('--eval_every',
                        help='evaluate every ____ rounds;',
                        type=int,
                        default=1)
    parser.add_argument('--clients_per_round',
                        help='number of clients trained per round;',
                        type=int,
                        default=num_users)
    parser.add_argument('--batch_size',
                        help='batch size when clients train on data;',
                        type=int,
                        default=batch_size
                        )  # 0 is full dataset
    parser.add_argument('--num_epochs',
                        help='number of epochs when clients train on data;',
                        type=int,
                        default=loc_ep)
    parser.add_argument('--learning_rate',
                        help='learning rate for inner solver;',
                        type=float,
                        default=learning_rate)  # 0.003
    parser.add_argument('--hyper_learning_rate',
                        help='learning rate for inner solver;',
                        type=float,
                        default=hyper_learning_rate)  # 0.001
    parser.add_argument('--mu',
                        help='constant for prox;',
                        type=float,
                        default=0.)  # 0.01
    parser.add_argument('--seed',
                        help='seed for randomness;',
                        type=int,
                        default=0)
    parser.add_argument('--weight',
                        help='enable weight value;',
                        type=int,
                        default=weight)
    parser.add_argument('--lamb',
                        help='Penalty value for proximal term;',
                        type=int,
                        default=lamb)
    parser.add_argument('--times',
                        help='Number of running time;',
                        type=int,
                        default=times)
    parser.add_argument('--rho',
                        help='Condition number only for synthetic data;',
                        type=int,
                        default=rho)
    try:
        parsed = vars(parser.parse_args())
    except IOError as msg:
        parser.error(str(msg))

    # Set seeds
    random.seed(1 + parsed['seed'])
    np.random.seed(12 + parsed['seed'])
    tf.set_random_seed(123 + parsed['seed'])

    # load selected model
    # all synthetic datasets use the same model
    if parsed['dataset'].startswith("synthetic"):
        model_path = '%s.%s.%s.%s' % (
            'flearn', 'models', 'synthetic', parsed['model'])
    else:
        model_path = '%s.%s.%s.%s' % (
            'flearn', 'models', parsed['dataset'], parsed['model'])

    # mod = importlib.import_module(model_path)
    import flearn.models.linear_synthetic.linear as linear
    mod = linear
    learner = getattr(mod, 'Model')

    # load selected trainer
    opt_path = 'flearn.trainers.%s' % parsed['optimizer']
    mod = importlib.import_module(opt_path)
    optimizer = getattr(mod, 'Server')

    # add selected model parameter
    parsed['model_params'] = MODEL_PARAMS['.'.join(
        model_path.split('.')[2:-1])]
    # parsed['model_params'] = MODEL_PARAMS['mnist.mclr']

    # print and return
    maxLen = max([len(ii) for ii in parsed.keys()])
    fmtString = '\t%' + str(maxLen) + 's : %s'
    print('Arguments:')
    for keyPair in sorted(parsed.items()):
        print(fmtString % keyPair)

    return parsed, learner, optimizer


def main(num_users=5, loc_ep=10, Numb_Glob_Iters=100, lamb=0, learning_rate=0.01, hyper_learning_rate= 0.01, alg='fedprox', weight=True, batch_size=0, times =10, rho = 0, dataset="mnist"):
    # suppress tf warnings
    tf.logging.set_verbosity(tf.logging.WARN)

    # parse command line arguments
    options, learner, optimizer = read_options(
        num_users, loc_ep, Numb_Glob_Iters, lamb, learning_rate,hyper_learning_rate, alg, weight, batch_size, times, rho, dataset)

    # read data
    train_path = os.path.join('data', options['dataset'], 'data', 'train')
    test_path = os.path.join('data', options['dataset'], 'data', 'test')
    dataset = read_data(train_path, test_path)

    # call appropriate trainer
    for i in range(times):
        # Set seeds
        random.seed(1 + i)
        np.random.seed(12 + i)
        tf.set_random_seed(123 + i)
        print('......time for runing......',i)
        t = optimizer(options, learner, dataset)
        t.train(i)
    average_data(num_users=num_users, loc_ep1=loc_ep, Numb_Glob_Iters=Numb_Glob_Iters, lamb=lamb, learning_rate=learning_rate, hyper_learning_rate = hyper_learning_rate, algorithms=alg, batch_size=batch_size, dataset=dataset, rho = rho, times = times)


if __name__ == '__main__':
    algorithms_list = ["fedfedl","fedfedl","fedfedl","fedfedl","fedfedl","fedfedl","fedfedl","fedfedl","fedfedl","fedfedl","fedfedl","fedfedl"] #fedfedl
    rho = [1.4, 1.4, 1.4, 1.4,  2 ,2 , 2, 2, 5, 5, 5, 5]
    lamb_value = [0, 0, 0, 0,  0, 0, 0, 0 , 0, 0, 0 ,0]
    learning_rate = [0.01,0.01,0.01,0.01, 0.01,0.01,0.01,0.01, 0.01,0.01,0.01,0.01]
    hyper_learning_rate = [0.1,0.3,0.5,0.7, 0.1,0.3,0.5,0.7, 0.1,0.3,0.5,0.7]
    local_ep = [20, 20, 20, 20,  20, 20, 20, 20,  20, 20, 20, 20]
    batch_size = [0,0,0,0 ,0,0,0,0, 0,0,0,0]
    DATA_SET = "linear_synthetic"
    number_users = 10

    #for i in range(len(algorithms_list)):
    #    main(num_users=number_users, loc_ep=local_ep[i], Numb_Glob_Iters=200, lamb=lamb_value[i],
    #         learning_rate=learning_rate[i],hyper_learning_rate=hyper_learning_rate[i],  alg=algorithms_list[i], batch_size=batch_size[i], rho = rho[i], dataset=DATA_SET)

    plot_summary_linear(num_users=number_users, loc_ep1=local_ep, Numb_Glob_Iters=200, lamb=lamb_value,
                               learning_rate=learning_rate, hyper_learning_rate = hyper_learning_rate, algorithms_list=algorithms_list, batch_size=batch_size, rho = rho, dataset=DATA_SET)
    print("-- FINISH -- :",)
