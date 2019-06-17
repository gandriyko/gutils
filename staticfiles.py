from django.conf import settings
from django.contrib.staticfiles.storage import ManifestStaticFilesStorage
from django.utils.encoding import force_text

import io
import json
import os


class PrivateManifestStaticFilesStorage(ManifestStaticFilesStorage):

    def read_manifest(self):
        manifest_location = os.path.abspath(os.path.join(
            settings.BASE_DIR, 'private', self.manifest_name))
        try:
            with io.open(manifest_location, encoding='utf-8') as manifest:
                return manifest.read()
        except IOError:
            return None

    def save_manifest(self):
        payload = {'paths': self.hashed_files, 'version': self.manifest_version}
        manifest_location = os.path.abspath(os.path.join(
            settings.BASE_DIR, 'private', self.manifest_name))
        if os.path.exists(manifest_location):
            os.remove(manifest_location)
        contents = force_text(json.dumps(payload))
        with io.open(manifest_location, 'w', encoding='utf-8') as manifest:
            manifest.write(contents)
