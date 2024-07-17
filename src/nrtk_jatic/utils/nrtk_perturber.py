import itertools
import logging
from typing import Iterable, List, Tuple

import numpy as np
from maite.protocols.object_detection import Dataset
from nrtk.interfaces.perturb_image_factory import PerturbImageFactory

from nrtk_jatic.interop.object_detection.augmentation import JATICDetectionAugmentation
from nrtk_jatic.interop.object_detection.dataset import JATICObjectDetectionDataset


def nrtk_perturber(
    maite_dataset: Dataset, perturber_factory: PerturbImageFactory
) -> Iterable[Tuple[str, Dataset]]:
    """Generate augmented dataset(s) of type maite.protocols.object_detection.Dataset.

    Generate augmented dataset(s) of type maite.protocols.object_detection.Dataset
    given an input dataset of the same type and a perturber factory
    implementation. Each perturber combination will result in a newly
    generated dataset.

    :param maite_dataset: A dataset object of type maite.protocols.object_detection.Dataset
    :param perturber_factory: PerturbImageFactory implementation.
    """
    perturber_factory_config = perturber_factory.get_config()
    if "theta_keys" in perturber_factory_config:  # pyBSM doesn't follow interface rules
        perturb_factory_keys = perturber_factory_config["theta_keys"]
        thetas = perturber_factory.thetas
    else:
        perturb_factory_keys = [perturber_factory.theta_key]
        thetas = [perturber_factory.thetas]

    perturber_combinations = [
        dict(zip(perturb_factory_keys, v)) for v in itertools.product(*thetas)
    ]
    logging.info(f"Perturber sweep values: {perturber_combinations}")

    # Iterate through the different perturber factory parameter combinations and
    # save the perturbed images to disk
    logging.info("Starting perturber sweep")
    augmented_datasets: List[Dataset] = []
    output_perturb_params: List[str] = []
    for i, (perturber_combo, perturber) in enumerate(
        zip(perturber_combinations, perturber_factory)
    ):
        output_perturb_params.append(
            "".join("_{!s}-{!s}".format(k, v) for k, v in perturber_combo.items())
        )

        logging.info(f"Starting perturbation for {output_perturb_params[i]}")

        aug_imgs = []
        aug_dets = []
        aug_metadata = []

        jatic_perturber = JATICDetectionAugmentation(augment=perturber)

        # Formatting data to be of batch_size=1 in order to support MAITE
        # detection protocol's expected input for Augmentation
        for idx in range(len(maite_dataset)):
            aug_img, aug_det, aug_md = jatic_perturber(
                batch=(
                    [maite_dataset[idx][0]],
                    [maite_dataset[idx][1]],
                    [maite_dataset[idx][2]],
                )
            )
            # Appending data to separate lists in order to handle images
            # of varying sizes
            aug_imgs.append(np.asarray(aug_img)[0])
            aug_dets.append(aug_det[0])
            aug_metadata.append(aug_md[0])

        augmented_datasets.append(
            JATICObjectDetectionDataset(aug_imgs, aug_dets, aug_metadata)
        )
    return zip(output_perturb_params, augmented_datasets)
