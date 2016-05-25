# coding:utf-8
import os
from bottle import static_file
from service import Service

__all__ = [ "FileService" ]

class FileService(Service):
    """static file download service"""
    def __init__(self, env, file_dir, image_dir, download_url, \
                 upload_password):
        super(FileService, self).__init__(env)
        self._static_dir = os.path.abspath(file_dir)
        self._imgae_dir = os.path.abspath(image_dir)
        self._download_url = download_url
        self._upload_password = upload_password

    def get_file(self, filename):
        return static_file(filename, root=self._static_dir)

    def get_static_dir(self):
        return self._static_dir

    def get_image_dir(self):
        return self._imgae_dir

    def get_download_url(self):
        return self._download_url

    def get_upload_password(self):
        return self._upload_password