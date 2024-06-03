import numpy as np
import pytest
from typing import Sequence

from maite.protocols.image_classification import TargetType

from nrtk_cdao.interop.image_classification.augmentation import JATICClassificationAugmentation
from nrtk_cdao.interop.image_classification.dataset import JATICImageClassificationDataset
from tests.utils.test_utils import ResizePerturber


class TestJATICImageClassificationDataset:
    @pytest.mark.parametrize("dataset, expected_lbls_out", [
        (
            JATICImageClassificationDataset(
                [np.random.randint(0, 255, (256, 256, 3), dtype=np.uint8),
                 np.random.randint(0, 255, (128, 128, 3), dtype=np.uint8)],
                [np.asarray([0]), np.asarray([1])],
                [{"some_metadata": 0}, {"some_metadata": 1}]
            ),
            [np.asarray([0]), np.asarray([1])],
        )
    ])
    def test_dataset_adapter(
        self,
        dataset: JATICImageClassificationDataset,
        expected_lbls_out: Sequence[TargetType]
    ) -> None:
        """
        Test that the dataset adapter takes in an input of varying size
        images with corresponding labels and metadata and can be ingested
        by the augmentation adapter object.
        """
        perturber = ResizePerturber(w=64, h=512)
        augmentation = JATICClassificationAugmentation(augment=perturber)
        for idx in range(len(dataset)):
            img_in = dataset[idx][0]
            lbl_in = dataset[idx][1]
            md_in = dataset[idx][2]

            # Get expected image and metadata from "normal" perturber
            expected_img_out = perturber(np.asarray(img_in))
            expected_md_out = dict(md_in)
            expected_md_out["nrtk::perturber"] = perturber.get_config()
            expected_md_out.update(
                {
                    "image_info": {
                        "width": expected_img_out.shape[1],
                        "height": expected_img_out.shape[0]
                    }
                }
            )

            # Apply augmentation via adapter
            img_out, lbl_out, md_out = augmentation((
                np.expand_dims(img_in, axis=0),
                lbl_in,
                [md_in]
            ))
            img_out = np.asarray(img_out)
            lbl_out = np.asarray(lbl_out)
            expected_lbl_out = np.asarray(expected_lbls_out[idx])

            # Check that expectations hold
            assert np.array_equal(img_out[0], expected_img_out)
            assert np.array_equal(lbl_out, expected_lbl_out)
            assert md_out[0] == expected_md_out
