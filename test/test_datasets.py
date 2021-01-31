# Copyright (C) 2021, Pyronear contributors.

# This program is licensed under the GNU Affero General Public License version 3.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl-3.0.txt> for full license details.

import unittest
import tempfile
from pathlib import Path
import json
import requests
from PIL.Image import Image
from torchvision.datasets import VisionDataset

from pyrovision import datasets


class DatasetsTester(unittest.TestCase):
    def test_downloadurl(self):
        # Valid input
        url = 'https://arxiv.org/pdf/1910.02940.pdf'

        with tempfile.TemporaryDirectory() as root:
            # URL error cases
            self.assertRaises(requests.exceptions.MissingSchema, datasets.utils.download_url,
                              'url', root, verbose=False)
            self.assertRaises(requests.exceptions.ConnectionError, datasets.utils.download_url,
                              'https://url', root, verbose=False)
            self.assertRaises(TypeError, datasets.utils.download_url, 0, root, verbose=False)

            # Root error cases
            self.assertRaises(TypeError, datasets.utils.download_url, url, 0, verbose=False)

            # Working case
            datasets.utils.download_url(url, root, verbose=True)
            self.assertTrue(Path(root, url.rpartition('/')[-1]).is_file())

    def test_downloadurls(self):
        # Valid input
        urls = ['https://arxiv.org/pdf/1910.01108.pdf', 'https://arxiv.org/pdf/1810.04805.pdf',
                'https://arxiv.org/pdf/1905.11946.pdf', 'https://arxiv.org/pdf/1910.01271.pdf']

        with tempfile.TemporaryDirectory() as root:
            # URL error cases
            self.assertRaises(requests.exceptions.MissingSchema, datasets.utils.download_urls,
                              ['url'] * 4, root, silent=False)
            self.assertRaises(requests.exceptions.ConnectionError, datasets.utils.download_urls,
                              ['https://url'] * 4, root, silent=False)
            self.assertRaises(TypeError, datasets.utils.download_url, [0] * 4, root, silent=False)

            # Working case
            datasets.utils.download_urls(urls, root, silent=False)
            self.assertTrue(all(Path(root, url.rpartition('/')[-1]).is_file() for url in urls))

    def test_openfire(self):
        num_samples = 200

        # Test img_folder argument: wrong type and default (None)
        with tempfile.TemporaryDirectory() as root:
            self.assertRaises(TypeError, datasets.OpenFire, root, download=True, img_folder=1)
            ds = datasets.OpenFire(root=root, download=True, num_samples=num_samples,
                                   img_folder=None)
            self.assertIsInstance(ds.img_folder, Path)

        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as img_folder:

            # Working case
            # Test img_folder as Path and str
            train_set = datasets.OpenFire(root=root, train=True, download=True, num_samples=num_samples,
                                          img_folder=Path(img_folder))
            test_set = datasets.OpenFire(root=root, train=False, download=True, num_samples=num_samples,
                                         img_folder=img_folder)
            # Check inherited properties
            self.assertIsInstance(train_set, VisionDataset)

            # Assert valid extensions of every image
            self.assertTrue(all(sample['name'].rpartition('.')[-1] in ['jpg', 'jpeg', 'png', 'gif']
                                for sample in train_set.data))
            self.assertTrue(all(sample['name'].rpartition('.')[-1] in ['jpg', 'jpeg', 'png', 'gif']
                                for sample in test_set.data))

            # Check against number of samples in extract (limit to num_samples)
            datasets.utils.download_url(train_set.url, root, filename='extract.json', verbose=False)
            with open(Path(root).joinpath('extract.json'), 'rb') as f:
                extract = json.load(f)[:num_samples]
            # Test if not more than 15 downloads failed.
            # Change to assertEqual when download issues are resolved
            self.assertAlmostEqual(len(train_set) + len(test_set), len(extract), delta=15)

            # Check integrity of samples
            img, target = train_set[0]
            self.assertIsInstance(img, Image)
            self.assertIsInstance(target, int)
            self.assertEqual(train_set.class_to_idx[extract[0]['target']], target)

            # Check train/test split
            self.assertIsInstance(train_set, VisionDataset)
            # Check unicity of sample across all splits
            train_paths = [sample['name'] for sample in train_set.data]
            self.assertTrue(all(sample['name'] not in train_paths for sample in test_set.data))


if __name__ == '__main__':
    unittest.main()
