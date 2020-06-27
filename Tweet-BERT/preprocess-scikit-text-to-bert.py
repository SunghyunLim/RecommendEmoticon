

from sklearn.model_selection import train_test_split
from sklearn.utils import resample
import functools
import multiprocessing

import pandas as pd
from datetime import datetime
import subprocess
import sys

subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'tensorflow==2.1.0'])
import tensorflow as tf
print(tf.__version__)

subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'transformers==2.8.0'])
from transformers import DistilBertTokenizer

from tensorflow import keras
import os
import re
import collections
import argparse
import json
import os
import pandas as pd
import csv
import glob
from pathlib import Path

tokenizer = DistilBertTokenizer.from_pretrained('distilbert-base-uncased')

DATA_COLUMN = 'TWEET'
LABEL_COLUMN = 'LABEL'
LABEL_VALUES = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    
label_map = {}
for (i, label) in enumerate(LABEL_VALUES):
    label_map[label] = i

class InputFeatures(object):
  """BERT feature vectors."""

  def __init__(self,
               input_ids,
               input_mask,
               segment_ids,
               label_id):
    self.input_ids = input_ids
    self.input_mask = input_mask
    self.segment_ids = segment_ids
    self.label_id = label_id
    
    
class Input(object):
  """A single training/test input for sequence classification."""

  def __init__(self, text, label=None):
    """Constructs an Input.
    Args:
      text: string. The untokenized text of the first sequence. For single
        sequence tasks, only this sequence must be specified.
      label: (Optional) string. The label of the example. This should be
        specified for train and dev examples, but not for test examples.
    """
    self.text = text
    self.label = label

def convert_input(text_input, max_seq_length):
    # First, we need to preprocess our data so that it matches the data BERT was trained on:
    #
    # 1. Lowercase our text (if we're using a BERT lowercase model)
    # 2. Tokenize it (i.e. "sally says hi" -> ["sally", "says", "hi"])
    # 3. Break words into WordPieces (i.e. "calling" -> ["call", "##ing"])
    # 
    # Fortunately, the Transformers tokenizer does this for us!
    #
    tokens = tokenizer.tokenize(text_input.text)    

    encode_plus_tokens = tokenizer.encode_plus(text_input.text,
                                               pad_to_max_length=True,
                                               max_length=max_seq_length)

    # Convert the text-based tokens to ids from the pre-trained BERT vocabulary
    input_ids = encode_plus_tokens['input_ids']
    # Specifies which tokens BERT should pay attention to (0 or 1)
    input_mask = encode_plus_tokens['attention_mask']
    # Segment Ids are always 0 for single-sequence tasks (or 1 if two-sequence tasks)
    segment_ids = [0] * max_seq_length

    # Label for our training data (star_rating 1 through 5)
    label_id = label_map[text_input.label]

    features = InputFeatures(
        input_ids=input_ids,
        input_mask=input_mask,
        segment_ids=segment_ids,
        label_id=label_id)

    return features

def convert_features_to_tfrecord(inputs,
                                 output_file,
                                 max_seq_length):
    """Convert a set of `Input`s to a TFRecord file."""

    tfrecord_writer = tf.io.TFRecordWriter(output_file)

    for (input_idx, text_input) in enumerate(inputs):
        if input_idx % 10000 == 0:
            print("Writing example %d of %d" % (input_idx, len(inputs)))

            bert_features = convert_input(text_input, max_seq_length)
        
            tfrecord_features = collections.OrderedDict()
            
            tfrecord_features['input_ids'] = tf.train.Feature(int64_list=tf.train.Int64List(value=bert_features.input_ids))
            tfrecord_features['input_mask'] = tf.train.Feature(int64_list=tf.train.Int64List(value=bert_features.input_mask))
            tfrecord_features['segment_ids'] = tf.train.Feature(int64_list=tf.train.Int64List(value=bert_features.segment_ids))
            tfrecord_features['label_ids'] = tf.train.Feature(int64_list=tf.train.Int64List(value=[bert_features.label_id]))

            tfrecord = tf.train.Example(features=tf.train.Features(feature=tfrecord_features))
            
            tfrecord_writer.write(tfrecord.SerializeToString())

    tfrecord_writer.close()

    
    
def list_arg(raw_value):
    """argparse type for a list of strings"""
    return str(raw_value).split(',')



    
def _transform_tsv_to_tfrecord(file, 
                               max_seq_length, 
                               balance_dataset):
    print('file {}'.format(file))
    print('max_seq_length {}'.format(max_seq_length))
    print('balance_dataset {}'.format(balance_dataset))

    filename_without_extension = Path(Path(file).stem).stem

    df = pd.read_csv(file, 
                     compression='gzip')

    df.isna().values.any()
    df = df.dropna()
    df = df.reset_index(drop=True)

    print('Shape of dataframe {}'.format(df.shape))

        
    print('Shape of dataframe before splitting {}'.format(df.shape))
    
    print('train split percentage {}'.format(args.train_split_percentage))
    print('validation split percentage {}'.format(args.validation_split_percentage))
    print('test split percentage {}'.format(args.test_split_percentage))    
    
    holdout_percentage = 1.00 - args.train_split_percentage
    print('holdout percentage {}'.format(holdout_percentage))
    df_train, df_holdout = train_test_split(df, 
                                            test_size=holdout_percentage, 
                                            stratify=df[LABEL_COLUMN])

    test_holdout_percentage = args.test_split_percentage / holdout_percentage
    print('test holdout percentage {}'.format(test_holdout_percentage))
    df_validation, df_test = train_test_split(df_holdout, 
                                              test_size=test_holdout_percentage,
                                              stratify=df_holdout[LABEL_COLUMN])
    
    df_train = df_train.reset_index(drop=True)
    df_validation = df_validation.reset_index(drop=True)
    df_test = df_test.reset_index(drop=True)

    print('Shape of train dataframe {}'.format(df_train.shape))
    print('Shape of validation dataframe {}'.format(df_validation.shape))
    print('Shape of test dataframe {}'.format(df_test.shape))

    train_inputs = df_train.apply(lambda x: Input(text = x[DATA_COLUMN], 
                                                         label = x[LABEL_COLUMN]), axis = 1)

    validation_inputs = df_validation.apply(lambda x: Input(text = x[DATA_COLUMN], 
                                                            label = x[LABEL_COLUMN]), axis = 1)

    test_inputs = df_test.apply(lambda x: Input(text = x[DATA_COLUMN], 
                                                label = x[LABEL_COLUMN]), axis = 1)

    # Next, we need to preprocess our data so that it matches the data BERT was trained on. For this, we'll need to do a couple of things (but don't worry--this is also included in the Python library):
    # 
    # 
    # 1. Lowercase our text (if we're using a BERT lowercase model)
    # 2. Tokenize it (i.e. "sally says hi" -> ["sally", "says", "hi"])
    # 3. Break words into WordPieces (i.e. "calling" -> ["call", "##ing"])
    # 4. Map our words to indexes using a vocab file that BERT provides
    # 5. Add special "CLS" and "SEP" tokens (see the [readme](https://github.com/google-research/bert))
    # 6. Append "index" and "segment" tokens to each input (see the [BERT paper](https://arxiv.org/pdf/1810.04805.pdf))
    # 
    # We don't have to worry about these details.  The Transformers tokenizer does this for us.
    # 
    train_data = '{}/bert/train'.format(args.output_data)
    validation_data = '{}/bert/validation'.format(args.output_data)
    test_data = '{}/bert/test'.format(args.output_data)

    # Convert our train and validation features to InputFeatures (.tfrecord protobuf) that works with BERT and TensorFlow.
    df_train_embeddings = convert_features_to_tfrecord(train_inputs, 
                                                       '{}/part-{}-{}.tfrecord'.format(train_data, args.current_host, filename_without_extension), 
                                                       max_seq_length)

    df_validation_embeddings = convert_features_to_tfrecord(validation_inputs, '{}/part-{}-{}.tfrecord'.format(validation_data, args.current_host, filename_without_extension), max_seq_length)

    df_test_embeddings = convert_features_to_tfrecord(test_inputs, '{}/part-{}-{}.tfrecord'.format(test_data, args.current_host, filename_without_extension), max_seq_length)
        
def parse_args():
    # Unlike SageMaker training jobs (which have `SM_HOSTS` and `SM_CURRENT_HOST` env vars), processing jobs to need to parse the resource config file directly
    resconfig = {}
    try:
        with open('/opt/ml/config/resourceconfig.json', 'r') as cfgfile:
            resconfig = json.load(cfgfile)
    except FileNotFoundError:
        print('/opt/ml/config/resourceconfig.json not found.  current_host is unknown.')
        pass # Ignore

    # Local testing with CLI args
    parser = argparse.ArgumentParser(description='Process')

    parser.add_argument('--hosts', type=list_arg,
        default=resconfig.get('hosts', ['unknown']),
        help='Comma-separated list of host names running the job'
    )
    parser.add_argument('--current-host', type=str,
        default=resconfig.get('current_host', 'unknown'),
        help='Name of this host running the job'
    )
    parser.add_argument('--input-data', type=str,
        default='/opt/ml/processing/input/data',
    )
    parser.add_argument('--output-data', type=str,
        default='/opt/ml/processing/output',
    )
    parser.add_argument('--train-split-percentage', type=float,
        default=0.90,
    )
    parser.add_argument('--validation-split-percentage', type=float,
        default=0.05,
    )    
    parser.add_argument('--test-split-percentage', type=float,
        default=0.05,
    )
    parser.add_argument('--balance-dataset', type=eval,
        default=False
    )
    parser.add_argument('--max-seq-length', type=int,
        default=128,
    )  
    
    return parser.parse_args()
        
    
def process(args):
    print('Current host: {}'.format(args.current_host))
    
    train_data = None
    validation_data = None
    test_data = None

    transform_tsv_to_tfrecord = functools.partial(_transform_tsv_to_tfrecord, 
                                                 max_seq_length=args.max_seq_length,
                                                 balance_dataset=args.balance_dataset

    )
    input_files = glob.glob('{}/*'.format(args.input_data))
    print("********** input files ***************")    
    print("args.input_data: ", args.input_data)
    print("input_files: ", input_files)

    num_cpus = multiprocessing.cpu_count()
    print('num_cpus {}'.format(num_cpus))

    p = multiprocessing.Pool(num_cpus)
    p.map(transform_tsv_to_tfrecord, input_files)

    print("********** Listing tf-record files ***************")        
    print('Listing contents of {}'.format(args.output_data))
    dirs_output = os.listdir(args.output_data)
    for file in dirs_output:
        print(file)

    print('Listing contents of {}'.format(train_data))
    dirs_output = os.listdir(train_data)
    for file in dirs_output:
        print(file)

    print('Listing contents of {}'.format(validation_data))
    dirs_output = os.listdir(validation_data)
    for file in dirs_output:
        print(file)

    print('Listing contents of {}'.format(test_data))
    dirs_output = os.listdir(test_data)
    for file in dirs_output:
        print(file)

    print('Complete')
    
    
if __name__ == "__main__":
    args = parse_args()
    print('################ START #######################')    
    print('Loaded arguments:')
    print(args)
    
    print('Environment variables:')
#     print(os.environ)

    process(args)    

