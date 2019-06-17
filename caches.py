from django.utils.encoding import force_bytes
from django.core.cache.backends.filebased import FileBasedCache
import hashlib
import os


class FileFolderBasedCache(FileBasedCache):

    def _key_to_file(self, key, version=None):
        key = self.make_key(key, version=version)
        self.validate_key(key)
        md5 = hashlib.md5(force_bytes(key)).hexdigest()
        filename = os.path.join(self._dir, md5[:3], ''.join([md5, self.cache_suffix]))
        directory = os.path.dirname(filename)
        if not os.path.exists(directory):
            current_mask = os.umask(0000)
            os.makedirs(directory)
            os.umask(current_mask)
        return filename
