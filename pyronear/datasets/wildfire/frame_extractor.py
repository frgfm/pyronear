import warnings

from functools import partial
from pathlib import Path
from typing import ClassVar, List, Union

import cv2
import numpy as np
import pandas as pd


class FrameExtractor:
    """Extract frames from wildfire videos according to a strategy

    Parameters
    ----------
    path_to_videos: str or Path
        Path leading to the full wildfire videos

    path_to_states: str or Path
        Path leading to CSV containing states.
        A state describes the scene between two frames keeping same labels
        Ex: Between frame 27 and 56, Fire seeable with confidence
        at position (x, y) but not located with confidence.
        Expected columns are:
        - stateStart and stateEnd: lower and upper frame labels encircling the state
        - fBase: name of the full videos from which to extract the frames

    strategy: str
        strategy to use in order to extract the frames.
        For now, two strategies are available:
        - 'random': extract randomly frames per state
        - 'uniform': extract evenly frames per state

    n_frames: int
        Number of frames as a parameter for extraction(for now, this is per state)

    Note: Here is an example of what a states CSV look like:
    states:
        fname	            fBase	fps fire  sequence	clf_confidence	loc_confidence	exploitable	   x	    y	    t	   stateStart	stateEnd
        0_seq0_344.mp4	    0.mp4	25	0	  0	        1	            0	            True          609.404	450.282	0.167  4	        344
        0_seq1061_1475.mp4	0.mp4	25	1	  0	        1	            0	            True          1027.524	558.621	2.015  1111	        1449
        0_seq446_810.mp4	0.mp4	25	1	  0	        1	            0	            True          695.737	609.404	1.473  483	        810


    Example
    -------
    frame_extractor = FrameExtractor("../WildFire",
                                     'jean_lulu_with_seq_01.states.csv',
                                     strategy='random',
                                     n_frames=2)

    labels = (frame_extractor.run(path_to_frames='koukou')
                             .get_frame_labels())
    """ # noqa
    strategies_allowed: ClassVar[List[str]] = ['random', 'evenly']

    def __init__(self,
                 path_to_videos: Union[str, Path],
                 path_to_states: Union[str, Path],
                 strategy: str = 'random',
                 n_frames: int = 2):

        self.path_to_videos = Path(path_to_videos)
        self.path_to_states = Path(path_to_states)
        self.strategy = strategy
        self.n_frames = n_frames

        if self.strategy not in self.strategies_allowed:
            raise ValueError(f"Strategy {self.strategy} is unknown."
                             f"Please choose from : {', '.join(self.strategies_allowed)}")

        self.states = pd.read_csv(path_to_states)

    def run(self, path_to_frames: Union[str, Path], allow_duplicates: bool = False, seed: int = 42):
        """Run the frame extraction on the videos according to given strategy and states

        path_to_frames: str or Path, path where to save the frames

        allow_duplicates: bool (default: False), whether or not to allow frames duplicates
            (One unique image(frame) may match multiple frames registered in labels

        seed: int, seed for random picking (default: 42)
        """
        # Define frames to extract given a strategy
        if (self.strategy == 'random'):
            random = True
        elif(self.strategy == 'evenly'):
            random = False

        labels = self._get_frame_labels(self.states, self.n_frames, random, allow_duplicates, seed)

        # Write labels
        path_to_frames = Path(path_to_frames)
        path_to_frames.mkdir(exist_ok=True)

        basename = self.path_to_states.stem
        path_to_frame_labels = path_to_frames / f'{basename}.labels.csv'
        print(f'Writing frame labels to {path_to_frame_labels}')
        labels.to_csv(path_to_frame_labels, index=False)
        self._labels = labels

        # Write frames
        print(f'Extracting {self.n_frames} frames per state ({len(labels)} in total) to {path_to_frames}')
        self._write_frames(labels, path_to_frames)
        return self

    def get_frame_labels(self) -> pd.DataFrame:
        return self._labels

    @staticmethod
    def _pick_frames(state: pd.Series, n_frames: int, random: bool,
                     allow_duplicates: bool, seed: int = 42) -> pd.Series:
        """
        Return a Series with the list of selected frames for the given state (n_frames x 1)

        Parameters
        ----------
        state: pd.Series containing stateStart, stateEnd and fBase

        n_frames: number of frames to pick

        allow_duplicates: bool, Whether or not to allow frames duplicates
            (One unique image(frame) may match multiple frames registered in labels

        random: bool
            Pick frames randomly or according to np.linspace,
            e.g. first if n_frames = 1, + last if n_frames = 2, + middle if n_frames = 3, etc

        seed: int, seed for random picking (default: 42)
        """
        np.random.seed(seed)

        # Trying to set a valid frame range
        frames_range = range(state.stateStart, state.stateEnd + 1)
        frames_range_len = len(frames_range)
        if frames_range_len < n_frames:
            if not allow_duplicates:
                raise ValueError(f"Not enough frames available({frames_range_len})"
                                 f" in the state to extract {n_frames} frames from {state.fBase}")
            else:
                warnings.warn(f"frames available({frames_range_len}) in the state"
                              f"are lower than the ones to extract ({n_frames}) from {state.fBase}."
                              f"Warning, they will be duplicates registered in labels but"
                              f"no duplicates as images because of unique filenames")

        # Let's pick frames according to strategy
        if random:
            # randomly select unique frame numbers within state range
            return pd.Series(np.random.choice(frames_range, size=n_frames, replace=allow_duplicates))
        else:
            # select evenly spaced frames within state range
            return pd.Series(np.linspace(state.stateStart, state.stateEnd, n_frames, dtype=int))

    def _get_frame_labels(self, states: pd.DataFrame, n_frames: int, random: bool,
                          allow_duplicates: bool = False, seed: int = 42) -> pd.DataFrame:
        """
        Given a DataFrame with states, call _pickFrames to create a DataFrame with
        n_frames per state containing the state information, filename and
        imgFile (the name of the file to be used when writing an image)

        Parameters
        ----------
        states: DataFrame containing fBase, stateStart, stateEnd

        n_frames: int, number of frames per state

        random: bool, pick frames randomly(True) or evenly(False)

        allow_duplicates: bool (default: False), whether or not to allow frames duplicates
            (One unique image(frame) may match multiple frames registered in labels

        seed: int, seed for pseudorandom generator
        """
        pick_frames_for_one_state = partial(self._pick_frames, n_frames=n_frames, random=random,
                                            allow_duplicates=allow_duplicates, seed=seed)
        # DataFrame containing columns (0..n_frames - 1)
        frames = states.apply(pick_frames_for_one_state, axis=1)  # (n_states x n_frames)

        # Merge states and frames and transform each value of the new columns into a row
        # Drop the new column 'variable' that represents the column name in frames
        df = pd.melt(states.join(frames), id_vars=states.columns,
                     value_vars=range(n_frames), value_name='frame').drop(columns=['variable'])

        # Add image file name
        df['imgFile'] = df.apply(lambda x: Path(x.fBase).stem + f'_frame{x.frame}.png', axis=1)
        return df.sort_values(['fBase', 'frame'])

    def _write_frames(self, labels: pd.DataFrame, path_to_frames: Union[str, Path]) -> None:
        """Extract frames from videos and write frames as
        <path_to_frames>/<fBase>_frame<frame>.png

        Parameters
        ----------
        labels: Pandas DataFrame containing:
            - fBase: filename of unsplit video (ex: 3.mp4)
            - frame: indexex of the frames to extract (ex: 56)
            - imgFile: filenames to save the frames (ex: 3_frame56.png)

        path_to_frames: str, output directory. Created if needed
        """
        path_to_frames = Path(path_to_frames)
        path_to_frames.mkdir(exist_ok=True)

        # For each video (ex: 3.mp4)
        for name, group in labels.groupby('fBase'):
            # Get the video
            movie = cv2.VideoCapture((self.path_to_videos / name).as_posix())
            # For each state
            for index, row in group.iterrows():
                # Position the video at the current frame
                movie.set(cv2.CAP_PROP_POS_FRAMES, row.frame)
                success, frame = movie.read()
                # Save the frame
                if success:
                    cv2.imwrite((path_to_frames / row.imgFile).as_posix(), frame)
                else:
                    raise IOError(f'Could not read frame {row.frame} from {name}')
