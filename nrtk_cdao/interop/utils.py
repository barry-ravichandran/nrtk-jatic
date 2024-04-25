import json
import kwcoco
import logging
import numpy as np
from pathlib import Path
from PIL import Image  # type: ignore
from typing import Any, Dict, List, Tuple

from maite.protocols.object_detection import Dataset


def _xywh_bbox_xform(x1: int, y1: int, x2: int, y2: int) -> Tuple[int, int, int, int]:
    return x1, y1, x2 - x1, y2 - y1


def dataset_to_coco(
    dataset: Dataset,
    output_dir: Path,
    img_filenames: List[Path],
    dataset_categories: List[Dict[str, Any]]
) -> None:
    """
    Save dataset object to file as a COCO formatted dataset.

    :param dataset: MAITE-compliant object detection dataset
    :param output_dir: The location where data will be saved.
    :param img_filenames: Filenames of images to be saved.
    :param dataset_categories: A list of the categories related to this dataset.
        Each dictionary should contain the following keys: id, name, supercategory.
    """
    if len(img_filenames) != len(dataset):
        raise ValueError(f"Image filename and dataset length mismatch ({len(img_filenames)} != {len(dataset)})")

    annotations = kwcoco.CocoDataset()
    for cat in dataset_categories:
        annotations.add_category(name=cat["name"], supercategory=cat["supercategory"], id=cat["id"])
    mod_metadata = list()

    for i in range(len(dataset)):
        image, dets, metadata = dataset[i]
        filename = output_dir / img_filenames[i]
        filename.parent.mkdir(parents=True, exist_ok=True)

        im = Image.fromarray(image)
        im.save(filename)

        labels = np.asarray(dets.labels)
        bboxes = np.asarray(dets.boxes)
        annotations.add_images([{'id': i, 'file_name': str(filename)}])
        for lbl, bbox in zip(labels, bboxes):
            annotations.add_annotation(
                image_id=i,
                category_id=int(lbl),
                bbox=list(
                    _xywh_bbox_xform(x1=int(bbox[0]), y1=int(bbox[1]), x2=int(bbox[2]), y2=int(bbox[3]))
                )
            )

        # PyBSM perturber is (as of currently) not JSON serializable
        # Modify metadata to be serializable
        # TODO: Remove once plugfigurable issues are solved
        if "nrtk::perturber" in metadata:
            config_keys = ["sensor", "scenario"]
            for cfg_key in config_keys:
                if cfg_key in metadata["nrtk::perturber"]:
                    for k, v in metadata["nrtk::perturber"][cfg_key].items():
                        if isinstance(v, np.ndarray):
                            metadata["nrtk::perturber"][cfg_key][k] = v.tolist()
            for k, v in metadata["nrtk::perturber"].items():
                if isinstance(v, np.ndarray):
                    metadata["nrtk::perturber"][k] = v.tolist()
        mod_metadata.append(metadata)
    logging.info(f"Saved perturbed images to {output_dir}")

    metadata_file = output_dir / "image_metadata.json"

    with open(metadata_file, "w") as f:
        json.dump(mod_metadata, f)
    logging.info(f"Saved image metadata to {metadata_file}")

    annotations_file = output_dir / "annotations.json"
    annotations.dump(annotations_file)
    logging.info(f"Saved annotations to {annotations_file}")
