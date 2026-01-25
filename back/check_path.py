import os

# The path where we THINK the model is
target_dir = os.path.join("analytics", "vision_models")

if os.path.exists(target_dir):
    print(f"--- Files found in {target_dir} ---")
    for f in os.listdir(target_dir):
        print(f"'{f}'")
else:
    print(f"❌ Error: The folder '{target_dir}' does not exist!")