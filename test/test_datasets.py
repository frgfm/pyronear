import unittest
import tempfile
from pathlib import Path
import json
import requests
from PIL.Image import Image
from torchvision.datasets import VisionDataset

from pyronear import datasets


class TestCollectEnv(unittest.TestCase):
    def test_downloadurl(self):
        # Valid input
        url = 'https://gist.githubusercontent.com/yrevar/942d3a0ac09ec9e5eb3a/raw/238f720ff059c1f82f368259d1ca4ffa5dd8f9f5/imagenet1000_clsidx_to_labels.txt'

        with Path(tempfile.TemporaryDirectory().name) as root:
            # URL error cases
            self.assertRaises(requests.exceptions.MissingSchema, datasets.utils.download_url, 'url', root, verbose=False)
            self.assertRaises(requests.exceptions.ConnectionError, datasets.utils.download_url, 'https://url', root, verbose=False)
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

        with Path(tempfile.TemporaryDirectory().name) as root:
            # URL error cases
            self.assertRaises(requests.exceptions.MissingSchema, datasets.utils.download_urls, ['url'] * 4, root, silent=False)
            self.assertRaises(requests.exceptions.ConnectionError, datasets.utils.download_urls, ['https://url'] * 4, root, silent=False)
            self.assertRaises(TypeError, datasets.utils.download_url, [0] * 4, root, silent=False)

            # Working case
            datasets.utils.download_urls(urls, root, silent=False)
            self.assertTrue(all(Path(root, url.rpartition('/')[-1]).is_file() for url in urls))

    def test_openfire(self):

        with Path(tempfile.TemporaryDirectory().name) as root:

            # Warning for missing train/test split
            self.assertWarns(UserWarning, datasets.OpenFire, root=root, download=True, valid_pct=None)

            # Working case
            # Check inherited properties
            dataset = datasets.OpenFire(root=root, train=True, download=True)
            self.assertIsInstance(dataset, VisionDataset)

            # Check against number of samples in extract
            datasets.utils.download_url(dataset.url, root, filename='extract.json', verbose=False)
            with open(root.joinpath('extract.json'), 'rb') as f:
                extract = json.load(f)
            # Uncomment when download issues are resolved
            # self.assertEqual(len(dataset), len(extract))

            # Check integrity of samples
            img, target = dataset[0]
            self.assertIsInstance(img, Image)
            self.assertIsInstance(target, int)
            self.assertEqual(dataset.class_to_idx[extract[0]['target']], target)

            # Check train/test split
            train_set = datasets.OpenFire(root=root, train=True, download=True, valid_pct=0.2)
            test_set = datasets.OpenFire(root=root, train=False, download=True, valid_pct=0.2)
            self.assertIsInstance(train_set, VisionDataset)
            # Check unicity of sample across all splits
            train_paths = [sample['path'] for sample in train_set.data]
            self.assertTrue(all(sample['path'] not in train_paths for sample in test_set.data))


if __name__ == '__main__':
    unittest.main()