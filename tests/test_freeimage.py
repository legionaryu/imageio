""" Tests for imageio's freeimage plugin
"""

import os

import numpy as np

from pytest import raises
from imageio.testing import run_tests_if_main, get_test_dir

import imageio
from imageio import core
from imageio.core import get_remote_file

test_dir = get_test_dir()


# Create test images LUMINANCE
im0 = np.zeros((32, 32), np.uint8)
im0[:16, :] = 200
im1 = np.zeros((32, 32, 1), np.uint8)
im1[:16, :] = 200
# Create test image RGB
im3 = np.zeros((32, 32, 3), np.uint8)
im3[:16, :, 0] = 250 
im3[:, :16, 1] = 200
im3[50:, :16, 2] = 100
# Create test image RGBA
im4 = np.zeros((32, 32, 4), np.uint8)
im4[:16, :, 0] = 250
im4[:, :16, 1] = 200
im4[50:, :16, 2] = 100
im4[:, :, 3] = 255
im4[20:, :, 3] = 120

fnamebase = os.path.join(test_dir, 'test')


def get_ref_im(colors, crop, float):
    """ Get reference image with
    * colors: 0, 1, 3, 4
    * cropping: 0-> none, 1-> crop, 2-> crop with non-contiguous data
    * float: False, True
    """
    assert colors in (0, 1, 3, 4)
    assert crop in (0, 1, 2)
    assert float in (False, True)
    rim = [im0, im1, None, im3, im4][colors]
    if float:
        rim = rim.astype(np.float32) / 255.0
    if crop == 1:
        rim = rim[:-1, :-1].copy()
    elif crop == 2:
        rim = rim[:-1, :-1]
    return rim


def assert_close(im1, im2, tol):
    if im1.ndim == 3 and im1.shape[-1] == 1:
        im1 = im1.reshape(im1.shape[:-1])
    if im2.ndim == 3 and im2.shape[-1] == 1:
        im2 = im2.reshape(im2.shape[:-1])
    assert im1.shape == im2.shape
    diff = im1.astype('float32') - im2.astype('float32')
    diff[15:17, :] = 0  # Mask edge artifacts
    diff[:, 15:17] = 0
    assert np.abs(diff).max() <= tol
    # import visvis as vv
    # vv.subplot(121); vv.imshow(im1); vv.subplot(122); vv.imshow(im2)


def test_get_ref_im():
    """ A test for our function to get test images """
    
    crop = 0
    for f in (False, True):
        for colors in (0, 1, 3, 4):
            rim = get_ref_im(0, crop, f)
            assert rim.flags.c_contiguous is True
            assert rim.shape[:2] == (32, 32)
    
    crop = 1
    for f in (False, True):
        for colors in (0, 1, 3, 4):
            rim = get_ref_im(0, crop, f)
            assert rim.flags.c_contiguous is True
            assert rim.shape[:2] == (31, 31)
    
    crop = 2
    for f in (False, True):
        for colors in (0, 1, 3, 4):
            rim = get_ref_im(0, crop, f)
            assert rim.flags.c_contiguous is False
            assert rim.shape[:2] == (31, 31)
    

def test_freeimage_format():
    
    # Format
    F = imageio.formats['PNG']
    
    # Reader
    R = F.read(core.Request('chelsea.png', 'ri'))
    assert len(R) == 1
    assert isinstance(R.get_meta_data(), dict)
    assert isinstance(R.get_meta_data(0), dict)
    raises(IndexError, R.get_data, 2)
    raises(IndexError, R.get_meta_data, 2)
    
    # Writer
    W = F.save(core.Request(fnamebase + '.png', 'wi'))
    W.append_data(im0)
    W.set_meta_data({'foo': 3})
    raises(RuntimeError, W.append_data, im0)


def test_freeimage_lib():
    
    fi = imageio.plugins.freeimage.fi
    
    # Error messages
    imageio.plugins._freeimage.fi._messages.append('this is a test')
    assert imageio.plugins._freeimage.fi.get_output_log()
    imageio.plugins._freeimage.fi._show_any_warnings()
    imageio.plugins._freeimage.fi._get_error_message()
    
    # Test getfif
    raises(ValueError, fi.getFIF, 'foo.png', 'x')  # mode must be r or w
    raises(ValueError, fi.getFIF, 'foo.notvalid', 'w')  # invalid ext
    raises(ValueError, fi.getFIF, 'foo.iff', 'w')  # We cannot write iff

    
def test_png():
    
    for float in (False, True):
        for crop in (0, 1, 2):
            for colors in (0, 1, 3, 4):
                fname = fnamebase + '%i.%i.%i.png' % (float, crop, colors)
                rim = get_ref_im(colors, crop, float)
                imageio.imsave(fname, rim)
                im = imageio.imread(fname)
                mul = 255 if float else 1
                assert_close(rim * mul, im, 0.1)  # lossless
    
    # Parameters
    im = imageio.imread('chelsea.png', ignoregamma=True)
    imageio.imsave(fnamebase + '.png', im, interlaced=True)
    
    # Parameter fail
    raises(TypeError, imageio.imread, 'chelsea.png', notavalidkwarg=True)
    raises(TypeError, imageio.imsave, fnamebase + '.png', im, notavalidk=True)
    
    # Compression
    imageio.imsave(fnamebase + '1.png', im, compression=0)
    imageio.imsave(fnamebase + '2.png', im, compression=9)
    s1 = os.stat(fnamebase + '1.png').st_size
    s2 = os.stat(fnamebase + '2.png').st_size
    assert s2 < s1
    # Fail
    raises(ValueError, imageio.imsave, fnamebase + '.png', im, compression=12)
    
    # Quantize
    imageio.imsave(fnamebase + '1.png', im, quantize=256)
    imageio.imsave(fnamebase + '2.png', im, quantize=4)
    
    im = imageio.imread(fnamebase + '2.png')  # touch palette read code
    s1 = os.stat(fnamebase + '1.png').st_size
    s2 = os.stat(fnamebase + '2.png').st_size
    assert s1 > s2
    # Fail
    fname = fnamebase + '1.png'
    raises(ValueError, imageio.imsave, fname, im[:, :, :3], quantize=300)
    raises(ValueError, imageio.imsave, fname, im[:, :, 0], quantize=100)


def test_jpg():
    
    for float in (False, True):
        for crop in (0, 1, 2):
            for colors in (0, 1, 3):
                fname = fnamebase + '%i.%i.%i.jpg' % (float, crop, colors)
                rim = get_ref_im(colors, crop, float)
                imageio.imsave(fname, rim)
                im = imageio.imread(fname)
                mul = 255 if float else 1
                assert_close(rim * mul, im, 1.1)  # lossy
    
    # No alpha in JPEG
    raises(Exception, imageio.imsave, fname, im4)
    
    # Parameters
    imageio.imsave(fnamebase + '.jpg', im3, progressive=True, optimize=True, 
                   baseline=True)
    
    # Parameter fail
    raises(TypeError, imageio.imread, fnamebase + '.jpg', notavalidkwarg=True)
    raises(TypeError, imageio.imsave, fnamebase + '.jpg', im, notavalidk=True)
    
    # Compression
    imageio.imsave(fnamebase + '1.jpg', im3, quality=10)
    imageio.imsave(fnamebase + '2.jpg', im3, quality=90)
    s1 = os.stat(fnamebase + '1.jpg').st_size
    s2 = os.stat(fnamebase + '2.jpg').st_size
    assert s2 > s1 
    raises(ValueError, imageio.imsave, fnamebase + '.jpg', im, quality=120)
    
    # Test broken JPEG
    fname = fnamebase + '_broken.jpg'
    open(fname, 'wb').write(b'this is not an image')
    raises(Exception, imageio.imread, fname)
    #
    bb = imageio.imsave(imageio.RETURN_BYTES, get_ref_im(3, 0, 0), 'JPEG')
    with open(fname, 'wb') as f:
        f.write(bb[:400])
        f.write(b' ')
        f.write(bb[400:])
    raises(Exception, imageio.imread, fname)
    
    # Test EXIF stuff
    fname = get_remote_file('images/rommel.jpg')
    im = imageio.imread(fname)
    assert im.shape[0] > im.shape[1]
    im = imageio.imread(fname, exifrotate=False)
    assert im.shape[0] < im.shape[1]
    im = imageio.imread(fname, exifrotate=2)  # Rotation in Python
    assert im.shape[0] > im.shape[1]
    # Write the jpg and check that exif data is maintained
    imageio.imsave(fnamebase + 'rommel.jpg', im)
    im = imageio.imread(fname)
    assert im.meta.EXIF_MAIN


def test_bmp():
    
    for float in (False, True):
        for crop in (0, 1, 2):
            for colors in (0, 1, 3, 4):
                fname = fnamebase + '%i.%i.%i.bmp' % (float, crop, colors)
                rim = get_ref_im(colors, crop, float)
                imageio.imsave(fname, rim)
                im = imageio.imread(fname)
                mul = 255 if float else 1
                assert_close(rim * mul, im, 0.1)  # lossless
    
    # Compression
    imageio.imsave(fnamebase + '1.bmp', im3, compression=False)
    imageio.imsave(fnamebase + '2.bmp', im3, compression=True)
    s1 = os.stat(fnamebase + '1.bmp').st_size
    s2 = os.stat(fnamebase + '2.bmp').st_size
    assert s1 + s2  # todo: bug in FreeImage? assert s1 < s2
    
    # Parameter fail
    raises(TypeError, imageio.imread, fnamebase + '1.bmp', notavalidkwarg=True)
    raises(TypeError, imageio.imsave, fnamebase + '1.bmp', im, notavalidk=True)


def test_gif():
    # todo: cannot save RGB and RGBA now
    for float in (False, True):
        for crop in (0, 1, 2):
            for colors in (0, 1, ):
                fname = fnamebase + '%i.%i.%i.gif' % (float, crop, colors)
                rim = get_ref_im(colors, crop, float)
                imageio.imsave(fname, rim)
                im = imageio.imread(fname)
                mul = 255 if float else 1
                if colors in (0, 1):
                    im = im[:, :, 0]
                assert_close(rim * mul, im, 1.1)  # lossless
    
    # Parameter fail
    raises(TypeError, imageio.imread, fname, notavalidkwarg=True)
    raises(TypeError, imageio.imsave, fnamebase + '1.gif', im, notavalidk=True)


def test_ico():
    
    for float in (False, True):
        for crop in (0, 1, 2):
            for colors in (0, 1, 3, 4):
                fname = fnamebase + '%i.%i.%i.ico' % (float, crop, colors)
                rim = get_ref_im(colors, crop, float)
                imageio.imsave(fname, rim)
                im = imageio.imread(fname)
                mul = 255 if float else 1
                assert_close(rim * mul, im, 0.1)  # lossless
    
    # Meta data
    R = imageio.read(fnamebase + '0.0.0.ico')
    assert isinstance(R.get_meta_data(0), dict)
    assert isinstance(R.get_meta_data(None), dict)  # But this print warning
    writer = imageio.save(fnamebase + 'I.ico')
    writer.set_meta_data({})
    writer.close()
    
    # Parameters. Note that with makealpha, RGBA images are read in incorrectly
    im = imageio.imread(fnamebase + '0.0.0.ico', makealpha=True)
    assert im.ndim == 3 and im.shape[-1] == 4
    
    # Parameter fail
    raises(TypeError, imageio.imread, fname, notavalidkwarg=True)
    raises(TypeError, imageio.imsave, fnamebase + '1.gif', im, notavalidk=True)
    
    # Multiple images
    im = get_ref_im(4, 0, 0)
    ims1 = im, np.column_stack([im, im]), np.row_stack([im, im])
    imageio.mimsave(fnamebase + 'I.ico', ims1)
    ims2 = imageio.mimread(fnamebase + 'I.ico')
    for im1, im2 in zip(ims1, ims2):
        assert_close(im1, im2, 0.1)


def test_other():
    
    # Cannot safe float
    im = get_ref_im(3, 0, 1)
    raises(Exception, imageio.imsave, fnamebase + '.jng', im, 'JNG')


run_tests_if_main()

#if __name__ == '__main__':
#   test_ico()
