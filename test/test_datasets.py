# Copyright (C) 2021, Pyronear contributors.

# This program is licensed under the GNU Affero General Public License version 3.
# See LICENSE or go to <https://www.gnu.org/licenses/agpl-3.0.txt> for full license details.

import unittest
import tempfile
from pathlib import Path
from PIL.Image import Image
import pandas as pd
import random
import requests
import torch
from torch.utils.data import DataLoader
from torchvision.transforms import transforms

from pyrovision import datasets


def generate_wildfire_dataset_fixture():
    random.seed(42)
    df = pd.DataFrame(columns=['imgFile', 'fire_id', 'fire'])
    for i in range(974):
        df = df.append({'imgFile': str(i).zfill(4) + '.jpg', 'fire_id': float(random.randint(1, 100)),
                        'fire': float(random.randint(0, 1))}, ignore_index=True)

    return df


def generate_wildfire_subsampler_dataset_fixture():
    df = pd.DataFrame(columns=['exploitable', 'fire', 'sequence', 'clf_confidence',
                               'loc_confidence', 'x', 'y', 't', 'stateStart',
                               'stateEnd', 'imgFile', 'fire_id', 'fBase'])
    for b in range(10):
        x = random.uniform(200, 500)
        y = random.uniform(200, 500)
        t = random.uniform(0, 100)
        start = random.randint(0, 200)
        end = random.randint(start + 11, 400)
        base = str(b) + '.mp4'
        imgsNb = random.sample(range(start, end), 10)
        imgsNb.sort()
        imgs = [str(b) + '_frame' + str(i) + '.png' for i in imgsNb]
        fire_id = float(random.randint(1, 100))
        fire = float(random.randint(0, 1))
        for i in range(10):
            df = df.append({'exploitable': True, 'fire': fire, 'sequence': 0,
                            'clf_confidence': 0, 'loc_confidence': 0, 'x': x, 'y': y, 't': t, 'stateStart': start,
                            'stateEnd': end, 'imgFile': imgs[i], 'fire_id': fire_id,
                            'fBase': base}, ignore_index=True)

    return df


def get_wildfire_image():

    # download image
    url = 'https://media.springernature.com/w580h326/nature-cms/uploads/collections/' \
          'Wildfire-and-ecosystems-Hero-d62e7fbbf36ce6915d4e3efef069ee0e.jpg'
    response = requests.get(url)
    # save image
    file = open("test//0003.jpg", "wb")
    file.write(response.content)
    file.close()


class OpenFireTester(unittest.TestCase):
    def test_openfire(self):
        tf = transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor()])
        with tempfile.TemporaryDirectory() as root:
            # Test train dataset
            ds_train = datasets.OpenFire(root=root, train=True, transform=tf, download=True, sample=True)
            self.assertEqual(len(ds_train), 64)
            x, trarget = ds_train[0]

            self.assertEqual(x.shape[1], 224)
            self.assertIsInstance(x, torch.Tensor)  # image correctly loaded ?
            self.assertIsInstance(trarget, int)  # target with correctly type

            # Test val dataset
            ds_val = datasets.OpenFire(root=root, train=False, transform=tf, download=True, sample=True)
            self.assertEqual(len(ds_val), 16)
            x, _ = ds_val[0]
            self.assertEqual(x.shape[1], 224)
            self.assertIsInstance(x, torch.Tensor)  # image correctly loaded ?

            # Test dataloader
            train_loader = torch.utils.data.DataLoader(ds_train, batch_size=8)
            val_loader = torch.utils.data.DataLoader(ds_val, batch_size=4, drop_last=False)

            self.assertEqual(len(train_loader), 8)
            self.assertEqual(len(val_loader), 4)

            x, y = next(iter(train_loader))
            self.assertEqual(x.shape, torch.Size([8, 3, 224, 224]))
            self.assertEqual(y.shape, torch.Size([8]))
            self.assertIsInstance(x, torch.Tensor)
            self.assertIsInstance(y[0].item(), int)


class WildFireDatasetTester(unittest.TestCase):

    def setUp(self):
        self.path_to_frames = Path(__file__).parent
        self.path_to_frames_str = str(self.path_to_frames)
        self.wildfire_path = Path(__file__).parent / 'wildfire_dataset.csv'
        self.wildfire_df = generate_wildfire_dataset_fixture()
        self.wildfire_df.to_csv(self.wildfire_path)
        get_wildfire_image()

    def test_wildfire_correctly_init_from_path(self):

        for path_to_frames in [self.path_to_frames, self.path_to_frames_str]:
            wildfire = datasets.wildfire.WildFireDataset(
                metadata=self.wildfire_path,
                path_to_frames=path_to_frames
            )

            self.assertEqual(len(wildfire), 974)
            self.assertEqual(len(wildfire[3]), 2)

    def test_wildfire_correctly_init_from_dataframe(self):
        for path_to_frames in [self.path_to_frames, self.path_to_frames_str]:
            wildfire = datasets.wildfire.WildFireDataset(
                metadata=self.wildfire_df,
                path_to_frames=path_to_frames
            )

            self.assertEqual(len(wildfire), 974)
            self.assertEqual(len(wildfire[3]), 2)

        # try to get one image of wildfire (item 3 is authorized image fixture)
        observation_3, metadata_3 = wildfire[3]
        self.assertIsInstance(observation_3, Image)  # image correctly loaded ?
        self.assertEqual(observation_3.size, (580, 326))
        # metadata correctly loaded ?
        self.assertTrue(torch.equal(metadata_3, torch.tensor([self.wildfire_df.loc[3]['fire']])))

    def test_wildfire_correctly_init_with_multiple_targets(self):
        wildfire = datasets.wildfire.WildFireDataset(
            metadata=self.wildfire_df,
            path_to_frames=self.path_to_frames,
            transform=transforms.ToTensor(),
            target_names=['fire', 'fire_id']
        )

        self.assertEqual(len(wildfire), 974)

        # try to get one image of wildfire (item 3 is authorized image fixture)
        observation_3, metadata_3 = wildfire[3]
        self.assertIsInstance(observation_3, torch.Tensor)  # image correctly loaded ?
        self.assertEqual(observation_3.size(), torch.Size([3, 326, 580]))
        self.assertTrue(torch.equal(metadata_3, torch.tensor([self.wildfire_df.loc[3]['fire'],
                                    self.wildfire_df.loc[3]['fire_id']])))  # metadata correctly loaded ?

    def test_invalid_csv_path_raises_exception(self):
        with self.assertRaises(ValueError):
            datasets.wildfire.WildFireDataset(
                metadata='bad_path.csv',
                path_to_frames=self.path_to_frames
            )

    def test_wildfire_correctly_init_with_transform(self):
        wildfire = datasets.wildfire.WildFireDataset(
            metadata=self.wildfire_path,
            path_to_frames=self.path_to_frames,
            transform=transforms.Compose([transforms.Resize((100, 66)), transforms.ToTensor()])
        )

        observation_3, _ = wildfire[3]
        self.assertEqual(observation_3.size(), torch.Size((3, 100, 66)))

    def test_dataloader_can_be_init_with_wildfire(self):
        wildfire = datasets.wildfire.WildFireDataset(metadata=self.wildfire_path,
                                                     path_to_frames=self.path_to_frames)
        DataLoader(wildfire, batch_size=64)


class WildFireSubSamplerTester(unittest.TestCase):

    def setUp(self):
        self.path_to_frames = Path(__file__).parent
        self.wildfire_path = Path(__file__).parent / 'wildfire_dataset.csv'
        self.wildfire_df = generate_wildfire_subsampler_dataset_fixture()
        self.wildfire_df.to_csv(self.wildfire_path)

    def test_good_size_after_subsamping(self):
        self.assertEqual(len(self.wildfire_df), 100)
        metadataSS = datasets.wildfire.computeSubSet(self.wildfire_df, 2)

        self.assertEqual(len(metadataSS), 20)

    def test_metadata_changes_each_time(self):
        metadataSS_1 = datasets.wildfire.computeSubSet(self.wildfire_df, 2, seed=1)
        metadataSS_2 = datasets.wildfire.computeSubSet(self.wildfire_df, 2, seed=2)

        self.assertEqual(len(metadataSS_1), 20)
        self.assertEqual(len(metadataSS_2), 20)
        self.assertFalse(metadataSS_1['imgFile'].values.tolist() == metadataSS_2['imgFile'].values.tolist())

    def test_metadata_does_not_changes_with_same_seed(self):
        metadataSS_1 = datasets.wildfire.computeSubSet(self.wildfire_df, 2, seed=1)
        metadataSS_2 = datasets.wildfire.computeSubSet(self.wildfire_df, 2, seed=1)

        self.assertEqual(len(metadataSS_1), 20)
        self.assertEqual(len(metadataSS_2), 20)
        self.assertTrue(metadataSS_1['imgFile'].values.tolist() == metadataSS_2['imgFile'].values.tolist())

    def test_increase_not_fire_semples(self):
        metadataSS = datasets.wildfire.computeSubSet(self.wildfire_path, 2, 1)

        self.assertGreater(len(metadataSS), 20)

    def test_invalid_csv_path_raises_exception(self):
        with self.assertRaises(ValueError):
            datasets.wildfire.computeSubSet(
                metadata='bad_path.csv',
                frame_per_seq=2
            )


class WildFireDatasetSplitter(unittest.TestCase):

    def setUp(self):
        self.path_to_frames = Path(__file__).parent

        self.wildfire_df = generate_wildfire_dataset_fixture()

        self.wildfire = datasets.wildfire.WildFireDataset(metadata=self.wildfire_df,
                                                          path_to_frames=self.path_to_frames)

    def test_consistent_ratios_good_init(self):
        ratios = {'train': 0.7, 'val': 0.15, 'test': 0.15}
        splitter = datasets.wildfire.WildFireSplitter(ratios)
        self.assertEqual(ratios, splitter.ratios)

    def test_inconsistent_ratios_raise_exception(self):
        ratios = {'train': 0.9, 'val': 0.2, 'test': 0.1}  # sum > 1
        with self.assertRaises(ValueError):
            datasets.wildfire.WildFireSplitter(ratios)

    def test_splitting_with_test_to_zero(self):
        ratios = {'train': 0.8, 'val': 0.2, 'test': 0}

        splitter = datasets.wildfire.WildFireSplitter(ratios, seed=42)
        splitter.fit(self.wildfire)

        for (set_, ratio_) in splitter.ratios_.items():
            self.assertAlmostEqual(ratio_, ratios[set_], places=1)

    def test_splitting_gives_good_splits_size(self):
        n_samples_expected = {'train': 688, 'val': 147, 'test': 139}
        ratios = {'train': 0.7, 'val': 0.15, 'test': 0.15}

        splitter = datasets.wildfire.WildFireSplitter(ratios, seed=42)
        splitter.fit(self.wildfire)

        self.assertEqual(splitter.n_samples_, n_samples_expected)
        for (set_, ratio_) in splitter.ratios_.items():
            self.assertAlmostEqual(ratio_, ratios[set_], places=1)

    def test_splitting_working_with_transforms(self):
        ratios = {'train': 0.7, 'val': 0.15, 'test': 0.15}
        transforms_expected = {'train': transforms.RandomCrop(10), 'val': None, 'test': None}

        splitter = datasets.wildfire.WildFireSplitter(ratios, transforms=transforms_expected)
        splitter.fit(self.wildfire)

        for (set_, transform_expected) in transforms_expected.items():
            self.assertIs(getattr(splitter, set_).transform, transform_expected)

    def test_splitting_with_unavailable_algorithm_raise_exception(self):
        ratios = {'train': 0.7, 'val': 0.15, 'test': 0.15}

        splitter = datasets.wildfire.WildFireSplitter(ratios, algorithm='wtf')
        with self.assertRaises(ValueError):
            splitter.fit(self.wildfire)


if __name__ == '__main__':
    unittest.main()
