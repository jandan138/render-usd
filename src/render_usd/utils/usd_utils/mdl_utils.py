import os
from pxr import Usd


def read_file(fn):
    with open(fn, 'r') as f:
        return f.read()
    return ''

def write_file(fn, content):
    with open(fn, 'w') as f:
        return f.write(content)

def fix_mdls(usd_path, default_mdl_path):
    base_path, base_name = os.path.split(usd_path)
    stage = Usd.Stage.Open(usd_path)
    pbr_mdl = read_file(default_mdl_path)
    need_to_save = False
    for prim in stage.TraverseAll():
        prim_attrs = prim.GetAttributes()
        for attr in prim_attrs:
            attr_type = attr.GetTypeName()
            if attr_type == "asset":
                attr_name = attr.GetName()
                attr_value = attr.Get()
                
                str_value = str(attr_value)
                if '@' in str_value and len(str_value) > 3:
                    names = str_value.split("@")
                    if names[1] != "OmniPBR.mdl":
                        if "Materials" not in names[1].split("/"):
                            # set new attribute value
                            new_value = "./Materials/" + names[1]
                            if os.path.exists(os.path.join(base_path, new_value)):
                                print(f"[GRGenerator: Mdl Utils] Set new value {new_value} to the {attr_name}")
                                attr.Set(new_value)
                                need_to_save = True
                            else:
                                print(f"[GRGenerator: Mdl Utils] Cannot find {new_value} in {os.path.join(base_path, './Materials/')}")
                            names[1] = "./Materials/" + names[1]

                        asset_fn = os.path.abspath(os.path.join(base_path, names[1]))
                        if not os.path.exists(asset_fn):
                            print(f"[GRGenerator: Mdl Utils] Find missing file {asset_fn}")
                            fdir, fname = os.path.split(asset_fn)
                            mdl_names = fname.split('.')
                            new_content = pbr_mdl.replace('Material__43', mdl_names[0])
                            write_file(asset_fn, new_content)
                        elif os.path.getsize(asset_fn) < 1:
                            print(f"[GRGenerator: Mdl Utils] Find wrong size file {asset_fn} {os.path.getsize(asset_fn)}")
    if need_to_save:
        stage.Save()
