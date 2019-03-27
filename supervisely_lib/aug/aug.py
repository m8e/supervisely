# coding: utf-8
import random
import numpy as np

from supervisely_lib.imaging import image

from supervisely_lib.annotation.annotation import Annotation
from supervisely_lib.geometry.image_rotator import ImageRotator
from supervisely_lib.geometry.rectangle import Rectangle
from supervisely_lib._utils import take_with_default


def _validate_image_annotation_shape(img: np.ndarray, ann: Annotation) -> None:
    if img.shape[:2] != ann.img_size:
        raise RuntimeError('Image shape {} doesn\'t match img_size {} in annotation.'.format(
            img.shape[:2], ann.img_size))


# Flips
def fliplr(img: np.ndarray, ann: Annotation) -> (np.ndarray, Annotation):
    """
    Flips an image array and annotation around vertical axis.

    Args:
        img: Input image array.
        ann: Input annotation.
    Returns:
        A tuple containing flipped image and annotation.
    """
    _validate_image_annotation_shape(img, ann)
    res_img = image.fliplr(img)
    res_ann = ann.fliplr()
    return res_img, res_ann


def flipud(img: np.ndarray, ann: Annotation) -> (np.ndarray, Annotation):
    """
    Flips an image array and annotation around horizontal axis.

    Args:
        img: Input image array.
        ann: Input annotation.
    Returns:
        A tuple containing flipped image and annotation.
    """
    _validate_image_annotation_shape(img, ann)
    res_img = image.flipud(img)
    res_ann = ann.flipud()
    return res_img, res_ann


# Crops
def crop(img: np.ndarray, ann: Annotation, top_pad: int = 0, left_pad: int = 0, bottom_pad: int = 0,
         right_pad: int = 0) -> (np.ndarray, Annotation):
    """
    Crops the given image array and annotation from all sides with the given values.

    Args:
        img: Input image array.
        ann: Input annotation.
        top_pad: The size in pixels of the piece of picture that will be cut from the top side.
        left_pad: The size in pixels of the piece of picture that will be cut from the left side.
        bottom_pad: The size in pixels of the piece of picture that will be cut from the bottom side.
        right_pad: The size in pixels of the piece of picture that will be cut from the right side.
    Returns:
        A tuple containing cropped image array and annotation.
    """
    _validate_image_annotation_shape(img, ann)
    height, width = img.shape[:2]
    crop_rect = Rectangle(top_pad, left_pad, height - bottom_pad - 1, width - right_pad - 1)

    res_img = image.crop(img, crop_rect)
    res_ann = ann.relative_crop(crop_rect)
    return res_img, res_ann


def crop_percent(img: np.ndarray, ann: Annotation, top: float = 0, left: float = 0, bottom: float = 0,
                 right: float = 0) -> (np.ndarray, Annotation):
    """
        Crops the given image array and annotation from all sides with the given percent values.

        Args:
            img: Input image array.
            ann: Input annotation.
            top: The relative size of the piece of picture that will be cut from the top side.
            left: The relative size  of the piece of picture that will be cut from the left side.
            bottom: The relative size  of the piece of picture that will be cut from the bottom side.
            right: The relative size  of the piece of picture that will be cut from the right side.
        Returns:
            A tuple containing cropped image array and annotation.
        """
    _validate_image_annotation_shape(img, ann)
    if not all(0 <= pad < 1 for pad in (top, left, right, bottom)):
        raise ValueError('All padding values must be between 0 and 1.')
    height, width = img.shape[:2]
    top_pixels = round(height * top)
    left_pixels = round(width * left)
    bottom_pixels = round(height * bottom)
    right_pixels = round(width * right)
    return crop(img, ann, top_pad=top_pixels, left_pad=left_pixels, bottom_pad=bottom_pixels,
                right_pad=right_pixels)


def random_crop(img: np.ndarray, ann: Annotation, height: int, width: int) -> (np.ndarray, Annotation):
    """
    Crops given image array and annotation at a random location.

    Args:
        img: Input image array.
        ann: Input annotation.
        height: Desired height of output crop.
        width: Desired width of output crop.
    Returns:
        A tuple containing cropped image array and annotation.
    """
    _validate_image_annotation_shape(img, ann)
    img_height, img_width = img.shape[:2]

    def calc_crop_pad(old_side, crop_side):
        new_side = min(int(old_side), int(crop_side))
        min_bound = random.randint(0, old_side - new_side)  # including [a; b]
        max_bound = old_side - min_bound - new_side
        return min_bound, max_bound

    left_pad, right_pad = calc_crop_pad(img_width, width)
    top_pad, bottom_pad = calc_crop_pad(img_height, height)
    return crop(img, ann, top_pad=top_pad, left_pad=left_pad, bottom_pad=bottom_pad, right_pad=right_pad)


def random_crop_percent(img: np.ndarray, ann: Annotation, height_portion_range: tuple, width_portion_range: tuple) ->\
        (np.ndarray, Annotation):
    """
    Crops given image array and annotation at a random location with random size lying in the set intervals.

    Args:
        img: Input image array.
        ann: Input annotation
        height_portion_range: Range of relative values [0, 1] to select output height from.
        width_portion_range: Range of relative values [0, 1] to select output width from.
    Returns:
         A tuple containing cropped image array and annotation.
    """
    _validate_image_annotation_shape(img, ann)
    img_height, img_width = img.shape[:2]

    height_p = random.uniform(height_portion_range[0], height_portion_range[1])
    width_p = random.uniform(width_portion_range[0], width_portion_range[1])
    crop_height = round(img_height * height_p)
    crop_width = round(img_width * width_p)
    return random_crop(img, ann, height=crop_height, width=crop_width)


# TODO factor out / simplify.
def _rect_from_bounds(padding_config: dict, img_h: int, img_w: int) -> Rectangle:
    def get_padding_pixels(raw_side, dim_name):
        side_padding_config = padding_config.get(dim_name)
        if side_padding_config is None:
            padding_pixels = 0
        elif side_padding_config.endswith('px'):
            padding_pixels = int(side_padding_config[:-len('px')])
        elif side_padding_config.endswith('%'):
            padding_fraction = float(side_padding_config[:-len('%')])
            padding_pixels = int(raw_side * padding_fraction / 100.0)
        else:
            raise ValueError(
                'Unknown padding size format: {}. Expected absolute values as "5px" or relative as "5%"'.format(
                    side_padding_config))
        return padding_pixels

    def get_padded_side(raw_side, l_name, r_name):
        l_bound = -get_padding_pixels(raw_side, l_name)
        r_bound = raw_side + get_padding_pixels(raw_side, r_name)
        return l_bound, r_bound

    left, right = get_padded_side(img_w, 'left', 'right')
    top, bottom = get_padded_side(img_h, 'top', 'bottom')
    return Rectangle(top=top, left=left, bottom=bottom, right=right)


def instances_crop(img: np.ndarray, ann: Annotation, class_title: str, padding_dct: dict = None) -> list:  # @TODO: pad_dict ???
    """
    Crops objects of specified classes from image with configurable padding.

    Args:
        img: Input image array.
        ann: Input annotation.
        class_title: Name of class to crop.
        padding_dct: Dict with padding
    Returns:

    """
    padding_dct = padding_dct or {}
    _validate_image_annotation_shape(img, ann)
    results = []
    img_rect = Rectangle.from_size(img.shape[:2])
    for label in ann.labels:
        if label.obj_class.name == class_title:
            src_fig_rect = label.geometry.to_bbox()
            new_img_rect = _rect_from_bounds(padding_dct, img_w=src_fig_rect.width, img_h=src_fig_rect.height)
            rect_to_crop = new_img_rect.translate(src_fig_rect.top, src_fig_rect.left)
            crops = rect_to_crop.crop(img_rect)
            if len(crops) == 0:
                continue
            rect_to_crop = crops[0]
            results.append((image.crop(img, rect_to_crop), ann.crop_labels(rect_to_crop)))
    return results


# Resize
def resize(img: np.ndarray, ann: Annotation, size: tuple) -> (np.ndarray, Annotation):
    """
    Resize the input image array and annotation to the given size.

    Args:
        img: Input image array.
        ann: Input annotation.
        size: Desired size (height, width) in pixels or -1. If one of values is -1 and "keep": true then for
                specific width height will be automatically computed to keep aspect ratio.
    Returns:
        A tuple containing resized image array and annotation.
    """
    _validate_image_annotation_shape(img, ann)
    height = take_with_default(size[0], -1)  # For backward capability
    width = take_with_default(size[1], -1)
    size = (height, width)

    new_size = image.restore_proportional_size(in_size=ann.img_size, out_size=size)
    res_img = image.resize(img, new_size)
    res_ann = ann.resize(new_size)
    return res_img, res_ann


# Resize
def scale(img: np.ndarray, ann: Annotation, frow: float = None, fcol: float = None, f: float = None) \
        -> (np.ndarray, Annotation):
    """
    Resize the input image array and annotation to the given size.

    Args:
        img: Input image array.
        ann: Input annotation.
        frow: Desired height scale height value
        frow: Desired width scale width value
        f: Desired height and width scale values in one
    Returns:
        A tuple containing resized image array and annotation.
    """
    _validate_image_annotation_shape(img, ann)
    new_size = image.restore_proportional_size(in_size=ann.img_size, frow=frow, fcol=fcol, f=f)
    res_img = image.resize(img, new_size)
    res_ann = ann.resize(new_size)
    return res_img, res_ann


# Rotate
class RotationModes:
    KEEP = 'keep'
    CROP = 'crop'


def rotate(img: np.ndarray, ann: Annotation, min_degrees: int, max_degrees: int, mode: str=RotationModes.KEEP) ->\
        (np.ndarray, Annotation):  # @TODO: add "preserve_size" mode
    """
    Rotates the image by random angle.

    Args:
        img: Input image array.
        ann: Input annotation.
        min_degrees: Lower bound of desired rotation angles range.
        max_degrees: Upper bound of desired rotation angles range.
        mode: parameter: "keep" - keep original image data, then new regions will be filled with black color;
            "crop" - crop rotated result to exclude black regions;
    Returns:
        A tuple containing rotated image array and annotation.
    """
    _validate_image_annotation_shape(img, ann)
    rotate_degrees = np.random.uniform(min_degrees, max_degrees)
    rotator = ImageRotator(img.shape[:2], rotate_degrees)

    if mode == RotationModes.KEEP:
        rect_to_crop = None

    elif mode == RotationModes.CROP:
        rect_to_crop = rotator.inner_crop

    else:
        raise NotImplementedError('Wrong black_regions mode.')

    res_img = rotator.rotate_img(img, use_inter_nearest=False)
    res_ann = ann.rotate(rotator)
    if rect_to_crop is not None:
        res_img = image.crop(res_img, rect_to_crop)
        res_ann = res_ann.crop(rect_to_crop)
    return res_img, res_ann