import cv2
import numpy as np
from torch.autograd import Variable
import torch
import math
import os
import urllib.request
import sys


from algos.flow_analysis.FlowNet2_src import flow_to_image
from algos.flow_analysis.FlowNet2_src import FlowNet2


model = []
path = os.path.dirname(__file__) + '/FlowNet2_src/pretrained/FlowNet2_checkpoint.pth.tar'

def reporthook(block_num, block_size, total_size):
    read_so_far = block_num * block_size
    if total_size > 0:
        percent = read_so_far * 1e2 / total_size
        s = "\r%5.1f%% %*d / %d" % (
            percent, len(str(total_size)), read_so_far, total_size)
        sys.stderr.write(s)
        if read_so_far >= total_size:  # near the end
            sys.stderr.write("\n")
    else:  # total size is unknown
        sys.stderr.write("read %d\n" % (read_so_far,))

flownet2 = FlowNet2()

if os.path.isfile(path):
    pretrained_dict = torch.load(path)['state_dict']
else:
    path1 = os.path.dirname(__file__) + '/FlowNet2_src/pretrained/'
    os.makedirs(path1)
    print('flow weights not found.. downloading ')

    urllib.request.urlretrieve(
        "http://download1589.mediafire.com/uiocw79svv9g/vrir61dv2ed93ty/FlowNet2_checkpoint.pth.tar", path , reporthook=reporthook)

    pretrained_dict = torch.load(path)['state_dict']

model_dict = flownet2.state_dict()
pretrained_dict = {k: v for k, v in pretrained_dict.items() if k in model_dict}
model_dict.update(pretrained_dict)
flownet2.load_state_dict(model_dict)

flownet2.cuda()

model = flownet2


def process_flow(frame, p_frame):
    height, width = frame.shape[:2]

    fr1 = cv2.resize(frame, (384, 512))
    fr2 = cv2.resize(p_frame, (384, 512))

    ims = np.array([[fr1, fr2]]).transpose((0, 4, 1, 2, 3)).astype(np.float32)
    ims = torch.from_numpy(ims)
    ims_v = Variable(ims.cuda(), requires_grad=False)

    flownet_2 = model
    flow_uv = flownet_2(ims_v).cpu().data
    flow_uv = flow_uv[0].numpy().transpose((1, 2, 0))

    # # CONVERT BACK TO ORIGINAL SCALE
    flow_uv = cv2.resize(flow_uv, (width, height))

    ave_flow_mag = []
    ave_flow_dir = []

    flow_uv_current = flow_uv

    mean_u = flow_uv_current[:, :, 0].mean()
    mean_v = flow_uv_current[:, :, 1].mean()

    mag = math.sqrt(math.pow(mean_u, 2) + math.pow(mean_v, 2))

    if mean_v < 0:
        uv_angle = 360 + math.degrees(math.atan2(mean_v, mean_u))
    else:
        uv_angle = math.degrees(math.atan2(mean_v, mean_u))
    direction = uv_angle / 360

    ave_flow_mag.append(mag)
    ave_flow_dir.append(direction)
    #
    # print('Ave flow direction = ', ave_flow_dir)
    # print('Ave flow Magnitude  = ', ave_flow_mag)
    flow_uv = flow_to_image(flow_uv)
    return flow_uv, ave_flow_mag, ave_flow_dir
