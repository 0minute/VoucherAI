from src.api.main import *
from test.constants import *

def test_create_workspace():
    result = post_create_workspace("test_workspace", "2025-01-01", "2025-01-31")
    print(result)

def test_kill_workspace():
    result = post_kill_workspace("test_workspace")
    print(result)

def test_list_workspaces():
    result = get_list_workspaces()
    print(result)

def test_update_workspace():
    result = patch_update_workspace("test_workspace", "2025-12-01")
    print(result)

def test_rename_workspace():
    result = patch_rename_workspace("test_workspace", "test_workspace_2")
    print(result)

def test_upload_images():
    testfile = TEST_IMAGE
    result = post_upload_images_with_domain("test_workspace", [testfile])
    print(result)

def test_upload_zip():
    testfile = TEST_ZIP
    result = post_upload_zip("test_workspace", testfile)
    print(result)

def test_get_uploaded_files():
    result = get_uploaded_files("test_workspace")
    print(result)





if __name__ == "__main__":

    test_create_workspace()
    # test_kill_workspace()
    # test_list_workspaces()
    # test_update_workspace()
    # test_rename_workspace()
    # test_upload_images()
    # test_upload_zip()
    # test_get_uploaded_files()