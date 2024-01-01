import os.path
import shutil

import rst

def assert_directories_equal(dir1, dir2):
    files1 = os.listdir(dir1)
    files2 = os.listdir(dir2)

    # check for differences in file listing
    for f in files1:
        if f not in files2:
            raise AssertionError(f'{f} is in {dir1} but not in {dir2}')
    for f in files2:
        if f not in files1:
            raise AssertionError(f'{f} is in {dir2} but not in {dir1}')

    for f in files1:
        file1 = os.path.join(dir1, f)
        file2 = os.path.join(dir2, f)
        if os.path.isdir(file1):
            if not os.path.isdir(file2):
                raise AssertionError(f'{file1} is a directory but {file2} is not')
            assert_directories_equal(file1, file2)
        else:
            if os.path.isdir(file2):
                raise AssertionError(f'{file2} is a directory but {file1} is not')
            with open(file1, 'rb') as fd:
                data1 = fd.read()
            with open(file2, 'rb') as fd:
                data2 = fd.read()
            if data1 != data2:
                raise AssertionError(f'contents of {file1} and {file2} do not match')

def test():
    if os.path.exists('test-output-actual'):
        shutil.rmtree('test-output-actual')

    os.mkdir('test-output-actual')

    with open(os.path.join('test-output-actual', 'test-script.output'), 'w') as outfile:
        st = rst.TemplatingState(outfile=outfile)
        st.process_filename('test/test-script.template')

    assert_directories_equal('test-output-expected', 'test-output-actual')

if __name__ == '__main__':
    test()

