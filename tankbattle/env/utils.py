# from scipy.misc import imresize
import  PIL
from PIL import Image
import time
import numpy as np
import torch

#工具

class Utils():
    WHITE = 0
    BLACK = 1
    GRAY = 2

    @staticmethod
    def get_current_time():#获取当前时间
        return int(round(time.time()))

    @staticmethod
    def get_color(color):#上色
        if color == Utils.WHITE:
            return (255, 255, 255)
        elif color == Utils.BLACK:
            return (0, 0, 0)
        elif color == Utils.GRAY:
            return (80, 80, 80)

    @staticmethod
    def process_state(state):
        """
        定义函数 process_state，用于对输入的原始图像进行预处理。
        它的输入是一个原始图像，(height, width, 3) 的 RGB 图像。
        它的输出是一个经过灰度化和缩放的图像，大小为 (84, 84)
        :param state:
        :return:
        """
        grayscale = np.dot(state[:, :, :3], [0.299, 0.587, 0.114])
        resize = np.array(Image.fromarray(grayscale).resize((84, 84),resample=PIL.Image.BILINEAR))
        return resize

    @staticmethod
    def resize_image(image):
        # 将RGB图像转换为PIL图像对象
        pil_image = Image.fromarray(image.astype('uint8'), 'RGB')
        # 调整大小为84x84像素
        resized_image = pil_image.resize((84, 84), resample=Image.BILINEAR)
        # 将图像转换为NumPy数组
        resized_image = np.array(resized_image)
        # 将数组的形状从(height, width, 3)转换为(3, 84, 84)
        resized_image = np.transpose(resized_image, (2, 0, 1))
        return resized_image

    @staticmethod
    def transpose_image(image):
        """
        将图片格式从 (height, width, in_channels) 转换为 (in_channels, height, width)
        :param image: 输入图像，ndarray 格式，形状为 (height, width, in_channels)
        :return: 转换后的图像，ndarray 格式，形状为 (in_channels, height, width)
        """
        return np.transpose(image, (2, 0, 1))

    @staticmethod
    def save_model(model, param_save_path, episode, epsilon, reward):
        # 保存一下我们的模型
        torch.save(model.state_dict(), f"{param_save_path}predicted_{episode}_{epsilon}_{reward}.pth")

    @staticmethod
    def load_model(model, path):
        model.load_state_dict(torch.load(path))
        return model

    @staticmethod
    def data_saving_format(data):
        str = ""
        for item in data:
            str += f"{item}\n"
        return str

    @staticmethod
    def save_data(data, path):
        # 将data保存到path路径下的txt文件中
        with open(path, 'w') as f:
            f.write(str(data))

