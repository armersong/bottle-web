import os

from application import Action
from bottle import request
from utils import gen_uuid

TMP_DIR='/tmp/images'
if not os.path.exists(TMP_DIR):
    os.mkdir(TMP_DIR, 0755)

class ImageAction(Action):
    def upload_image(self):
        file   = request.files.get('file')
        name, ext = os.path.splitext(file.filename)
        ext = ext[1:]
        src = os.path.join(TMP_DIR, '%s.%s' % (gen_uuid(), ext))
        file.save(src)

        try:
            dst_dir = self.file_service.get_image_dir()
            filename = self.image_service.save(src, dst_dir, ext)
            os.unlink(src)
            return dict(img_id=filename)
        except Exception as exc:
            os.unlink(src)
            raise
