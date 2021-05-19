# Wildfire classification

The goal here is to propose a training script and a dataset to train a wildfire classification model. 

This script allows you to train a wildfire binary classification model. You can train here all models available on [Holocron](https://github.com/frgfm/Holocron/tree/master/holocron/models) repository

You can either follow the procedure below to train the model on your own machine or click on the following collab link to use our training notebook on remote servers for free.


[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/gist/MateoLostanlen/1300692a2ab41418276b455f4eeab64c/train-wildfire.ipynb)

## Install

Install pyro-vision first

```bash
pip install pyronear
```

## Train

### OpenFire

You can also use freely our open-source dataset

```
python train.py OpenFire/ --use-openfire --model rexnet1_0x --lr 1e-3 -b 16 --epochs 20 --opt radam --sched onecycle --device 0
```

### Wildfire

This dataset is private, for now only Pyronear members can access it

```
python train.py WildFireLght/ --model rexnet1_0x --lr 1e-3 -b 16 --epochs 20 --opt radam --sched onecycle --device 0
```

