import bpy

def main():
    print("=== INSPECTING EYE DRIVERS ===")
    rig_obj = bpy.data.objects.get("CC_Base_Body_Rig")
    if not rig_obj:
        print("Rig CC_Base_Body_Rig not found!")
        return
        
    print(f"Rig: {rig_obj.name}")
    
    # Check custom properties on CTRL-eyes_look
    ctrl_eyes = rig_obj.pose.bones.get("CTRL-eyes_look")
    if ctrl_eyes:
        print("\n--- CTRL-eyes_look CUSTOM PROPERTIES ---")
        for prop in ctrl_eyes.keys():
            print(f"Property: {prop}, Value: {ctrl_eyes[prop]}")
    else:
        print("CTRL-eyes_look bone not found!")
        
    # Check drivers
    print("\n--- FCURVE DRIVERS ---")
    if rig_obj.animation_data:
        for d in rig_obj.animation_data.drivers:
            print(f"Driver on Data Path: {d.data_path}, Array Index: {d.array_index}")
            driver = d.driver
            print(f"  Type: {driver.type}, Expression: '{driver.expression}'")
            for var in driver.variables:
                print(f"  Variable: {var.name}, Type: {var.type}")
                for target in var.targets:
                    print(f"    Target ID: {target.id}, Path: '{target.data_path}'")
            if len(d.modifiers) > 0:
                print(f"  Generator Coefficients: {list(d.modifiers[0].coefficients)}")
    else:
        print("No animation data / drivers found on rig!")

if __name__ == "__main__":
    main()
