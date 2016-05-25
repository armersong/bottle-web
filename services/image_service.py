# coding:utf-8
import os
from PIL import Image
from utils import gen_uuid
from service import Service

__all__ = [ "ImageService" ]

FORMATS = ('jpg', '.png', '.gif')

class ImageServiceError(RuntimeError):
    pass

class ImageServiceFormatError(ImageServiceError):
    pass

class ImageService(Service):
    """image convert service"""
    def __init__(self, env, quality, small, medium, big):
        super(ImageService, self).__init__(env)
        self._quality = quality
        self._specs = dict(small=small, medium=medium, big=big)

    def save(self, src, dst_dir, format='jpg', default_format='jpg'):
        '''
        convert to multi-size
        :param src:
        :param dst_dir:
        :param format: jpg or png
        :return: image filename
        '''
        if format.lower() not in FORMATS:
            if (default_format is None) or (default_format != ''):
                raise ImageServiceFormatError
            else:
                format = default_format
        img_id = gen_uuid()
        filename = '%s.%s' % (img_id,format)
        for name,size in self._specs.items():
            image = Image.open(src)
            image.thumbnail((size,size))
            path = os.path.join(dst_dir,name)
            if not os.path.exists(path):
                os.mkdir(path, 0755)
            image.save(os.path.join(path,filename), quality=self._quality)
        return filename

