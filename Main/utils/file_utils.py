# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import os
import math
import mimetypes
from PIL import Image
from tinytag import TinyTag
from ._validators import is_url
from .file_helpers import run_in_exc
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata


class FileHelpers:
    def __init__(self, file, client=None) -> None:
        self.__file__ = file
        self.__client__ = client
        if not os.path.exists(self.__file__) and not is_url(self.__file__):
            raise OSError("File Doesn't exists in my storage.")

    @property
    def get_meta_data_video_hachoir(self):
        if metadata := extractMetadata(createParser(self.__file__)):
            dur = metadata.get("duration")
            width = metadata.get("width")
            height = metadata.get("height")
            return dur, width, height
        return None, None, None

    @run_in_exc
    def _get_metadata(self, is_audio=True):
        file = self.__file__
        attr = TinyTag.get(file)
        if is_audio:
            dur = int(attr.duration or 0)
            title = attr.composer or attr.title or attr.albumartist or None
            return dur, title
        else:
            dur = int(attr.duration or self.get_meta_data_video_hachoir[0] or 0)
            width = int(self.get_meta_data_video_hachoir[1] or 0)
            height = int(self.get_meta_data_video_hachoir[2] or 0)
            return dur, width, height

    @run_in_exc
    def _resize_if_req(self, image_size_allowded=1280):
        image = self.__file__
        im = Image.open(image)
        if (im.width and im.height) < image_size_allowded:
            size1 = im.width
            size2 = im.height
            if im.width > im.height:
                scale = image_size_allowded / size1
                size1new = image_size_allowded
                size2new = size2 * scale
            else:
                scale = image_size_allowded / size2
                size1new = size1 * scale
                size2new = image_size_allowded
            size1new = math.floor(size1new)
            size2new = math.floor(size2new)
            sizenew = (size1new, size2new)
            im = im.resize(sizenew)
        else:
            maxsize = (image_size_allowded, image_size_allowded)
            im.thumbnail(maxsize)
        im.save(image)
        return image

    @property
    def get_using_hachoir(self):
        metadata = extractMetadata(createParser(self.__file__))
        if metadata and metadata.has("mime_type"):
            return metadata.get("mime_type")

    @property
    def guess_mime_type_from_mimetypes(self):
        file_ = self.__file__
        if self.__client__:
            return self.__client__.guess_mime_type(file_)
        return mimetypes.guess_type(file_)[0]

    @property
    def guess_mime_type(self):
        return self.get_using_hachoir or self.guess_mime_type_from_mimetypes

    @property
    def is_audio(self):
        mt = self.guess_mime_type
        if mt and mt.startswith("audio/"):
            return True

    @property
    def is_audio_note(self):
        mt = self.guess_mime_type
        if mt and mt.startswith("audio/"):
            return bool(mt.endswith((".ogg")))

    @property
    def is_video(self):
        mt = self.guess_mime_type
        if mt and mt.startswith("video/"):
            return True

    @property
    def is_photo(self):
        mt = self.guess_mime_type
        if mt and mt.startswith("image/"):
            return True

    @property
    def get_ext(self):
        file_ = self.__file__
        if file_ and "." in file_:
            return file_.split(".", 1)[1]

    @property
    def is_animated_sticker(self):
        if not (
            self.is_audio or self.is_video or self.is_photo or self.is_sticker
        ) and self.get_ext in [".tgs"]:
            return True

    @property
    def is_sticker(self):
        if not (self.is_audio or self.is_video or self.is_photo) and self.get_ext in [
            ".webp"
        ]:
            return True

    @property
    def is_document(self):
        if not (
            self.is_audio
            or self.is_video
            or self.is_photo
            or self.is_sticker
            or self.is_animated_sticker
        ):
            return True
