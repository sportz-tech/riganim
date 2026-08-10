# utils/naming.py

# Prefix conventions
PREFIX_DEFORM = "DEF-"
PREFIX_CONTROL = "CTRL-"
PREFIX_MECHANISM = "MCH-"
PREFIX_ORG = "ORG-"

def get_deform_name(base_name):
    return f"{PREFIX_DEFORM}{base_name}"

def get_control_name(base_name):
    return f"{PREFIX_CONTROL}{base_name}"

def get_mch_name(base_name):
    return f"{PREFIX_MECHANISM}{base_name}"

def get_org_name(base_name):
    return f"{PREFIX_ORG}{base_name}"

def get_opposite_side_name(name):
    """Flips the side suffix of a bone name (e.g. bone.L -> bone.R)."""
    if name.endswith(".L"):
        return name[:-2] + ".R"
    elif name.endswith(".R"):
        return name[:-2] + ".L"
    elif name.endswith("_L"):
        return name[:-2] + "_R"
    elif name.endswith("_R"):
        return name[:-2] + "_L"
    return name
