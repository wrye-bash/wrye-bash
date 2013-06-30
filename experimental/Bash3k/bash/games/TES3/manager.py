dirs = {}
images = {}

_resource_table = {}

def init():
    """Initialize anything that isn't GUI dependent."""
    import os
    dirs['img'] = os.path.join(os.path.dirname(__file__), 'images')
    _resource_table['tab_close'] = os.path.join(dirs['img'], 'transparent16.gif')
    _resource_table['tab_close_active'] = os.path.join(dirs['img'], 'checkbox_green_off.gif')
    _resource_table['tab_close_pressed'] = os.path.join(dirs['img'], 'checkbox_green_on.gif')

def get_resource(resource_name, resource):
    return _resource_table.get(resource_name, resource)

