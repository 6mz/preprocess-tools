# -*- coding: utf-8 -*-
import os
from PIL import Image
import numpy as np
from bs4 import BeautifulSoup

from datasets_func import ReadList, SaveList
'''
本文件用于生成切片素材（图像及mask）
使用的是VOC数据集
'''


class Annotations(object):
    # 用于读取并保存xml文件中存储的对象的属性
    def __init__(self, bs_obj):
        self.name = bs_obj.find('name').string
        self.pose = str(bs_obj.find('pose').string)
        self.diff = int(bs_obj.find('difficult').string)
        self.trun = int(bs_obj.find('truncated').string)
        self.xmin = int(bs_obj.find('xmin').string)
        self.ymin = int(bs_obj.find('ymin').string)
        self.xmax = int(bs_obj.find('xmax').string)
        self.ymax = int(bs_obj.find('ymax').string)

    def GetBox(self):
        return (self.xmin, self.ymin, self.xmax, self.ymax)


class ListMannager(object):
    def __init__(self):
        '''
        列表管理类
        '''
        self.names = {}

    def NewList(self, name):
        self.names[name] = []

    def Add(self, name, item):
        # 添加一项
        if name in self.names:
            self.names[name].append(item)
        else:
            self.names[name] = []
            self.names[name].append(item)

    def Adds(self, name, lists):
        # 添加列表
        if name in self.names:
            self.names[name].extend(lists)
        else:
            self.names[name] = []
            self.names[name].extend(lists)

    def Del(self, name=None):
        if name is None:
            self.names = {}
        if name in self.names:
            del self.names[name]
        else:
            print(f'WARRING:{name} not exist')

    def Reset(self, name):
        if name in self.names:
            self.names[name] = []
        else:
            print(f'WARRING:{name} not exist')

    def Merging(self, sub):
        # 合并两个ListMannager对象，同名合并列表，不同名直接添加到dict中
        assert isinstance(sub, ListMannager)
        for name in sub.names:
            self.Adds(name, sub.names[name])

    def Save(self, name, fname):
        if name in self.names:
            SaveList(fname, self.names[name])
        else:
            print(f'WARRING:{name} not exist')

    def Open(self, name, fname):
        if name in self.names:
            self.Adds(name, ReadList(fname))
        else:
            self.names[name] = ReadList(fname)

    def QuickSave(self, path):
        # 快速储存列表成txt到path下，使用字典的key(names)直接当成文件名
        for list_name in self.names:
            fname = os.path.join(path, str(list_name)+'.txt')
            self.Save(list_name, fname)

    def QuickOpen(self, path):
        # 快速读取path下所有txt文件里的列表
        fileList = os.listdir(path)
        for file in fileList:
            b, e = os.path.splitext(file)
            if e != '.txt':
                continue
            full_name = os.path.join(path, file)
            self.Open(b, full_name)

    def Len(self, name):
        # 读取某个列表的长度
        if name in self.names:
            return len(self.names[name])
        else:
            return 0

    def Lens(self):
        # 读取全部列表的长度总和
        tlen = 0
        for key in self.names:
            tlen += self.Len(key)
        return tlen

    def Get(self, nameList, mode=0):
        # mode==0 : 合并列表
        # mode==1 ： 不合并列表（返回一个二级列表）
        res = []
        for name in nameList:
            if name in self.names:
                dataList = self.names[name]
            else:
                dataList = []
            if(mode):
                res.append(dataList)
            else:
                res.extend(dataList)
        return res

    def __getitem__(self, name):
        return self.names[name]


# ==========================================
#                 用于生成
# ==========================================
def ReadSegList(root_path):
    # 读入用于分割的文件名列表
    segList_path = os.path.join(root_path, 'ImageSets\\Segmentation')
    fname = 'trainval.txt'
    segList_name = os.path.join(segList_path, fname)
    segList = ReadList(segList_name)
    return segList


def GetAnnoList(root_path, namelist):
    # 按顺序生成xml文件列表
    annotations_path = os.path.join(root_path, 'Annotations')
    segAnnoList = [os.path.join(annotations_path, n+'.xml') for n in namelist]
    return segAnnoList


def GetImgList(root_path, namelist):
    # 按顺序生成图像文件列表
    img_path = os.path.join(root_path, 'JPEGImages')
    segImgList = [os.path.join(img_path, n+'.jpg') for n in namelist]
    return segImgList


def GetMaskList(root_path, namelist):
    # 按顺序生成图像文件列表
    mask_path = os.path.join(root_path, 'SegmentationObject')
    segMaskList = [os.path.join(mask_path, n+'.png') for n in namelist]
    return segMaskList


def ReadAnnotations(fname):
    # 解读xml文件，返回一个Annotations类
    with open(fname) as f:
        soup = BeautifulSoup(f.read(), "lxml")
    if not str(soup.segmented.string) == '1':
        print(f'WARRING:{fname} segmented tag is not 1')
        return None
    objs = soup.find_all('object')
    annos = []
    for obj in objs:
        annos.append(Annotations(obj))
    return annos


DEFAULT_GenMaterial_OPTIONS = {
        'out_path': 'Target',
        'classify_diff': True
        }


def GenMaterial(
        sName, annoName, imgName, maskName, opts=DEFAULT_GenMaterial_OPTIONS):
    # 对图像进行切割提取生成小素材
    annos = ReadAnnotations(annoName)
    if annos is None:
        return None
    localAnno = ListMannager()
    img = Image.open(imgName)
    mask = Image.open(maskName)
    maskArray = np.array(mask)
    imgArray = np.array(img)
    for i, anno in enumerate(annos):
        # 如果有遮挡就跳过
        if anno.trun:
            continue
        # 切片保存
        xmin, ymin, xmax, ymax = anno.GetBox()
        imgSlice = imgArray[ymin:ymax, xmin:xmax]
        maskSlice = maskArray[ymin:ymax, xmin:xmax]
        maskSlice = (maskSlice == (i+1))  # 第N个obj对应的mask编号是N+1
        imgSlice_ = ProcessImg(imgSlice, maskSlice)
        imgs = Image.fromarray(np.uint8(imgSlice_))
        masks = Image.fromarray(np.uint8(maskSlice)*255)
        imN, maN = GenMaterialName(opts, sName, i, anno)
        imgs.save(imN)
        masks.save(maN)
        # 保存分类列表
        localAnno.Add('name_'+anno.name, imN+'+'+maN)
        localAnno.Add('diff_'+str(anno.diff), imN+'+'+maN)
        localAnno.Add('pose_'+anno.pose, imN+'+'+maN)
        localAnno.Add(ShapeLevel(anno.GetBox()), imN+'+'+maN)
    return localAnno


def ProcessImg(imgArray, maskArray):
    # 给图像加上mask
    shape = maskArray.shape
    maskArray = maskArray.repeat(3)
    maskArray = maskArray.reshape((shape[0], shape[1], 3))
    imgArray = np.uint8(imgArray * maskArray)
    return imgArray


def ShapeLevel(box):
    # 生成图像大小级别
    xmin, ymin, xmax, ymax = box
    x = xmax - xmin
    y = ymax - ymin
    level = 'level_' + str(x//50*50) + '_' + str(y//50*50)
    return level


def GenMaterialName(opts, sName, i, anno):
    assert isinstance(anno, Annotations)
    out_path = opts['out_path']
    diff = 'diff' + str(anno.diff) if opts['classify_diff'] else ''
    itemName = anno.name
    fdir = os.path.join(out_path, itemName, diff)
    imName = os.path.join(fdir, sName+f'_{i}_im.png')
    maName = os.path.join(fdir, sName+f'_{i}_ma.png')
    if not os.path.exists(fdir):
        print(f'INFO: GenMaterialName: Create folder {fdir}')
        os.makedirs(fdir)
    return (imName, maName)


# ==========================================
#                 用于读取
# ==========================================
def GetImgAndMask(name):
    imName, maName = name.split('+')
    img = np.array(Image.open(imName))
    mask = np.array(Image.open(maName))
    return (img, mask)
