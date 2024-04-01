import os
import re


def update_version(root_folder):
    # Walk through all subdirectories and files
    for folder_name, _, files in os.walk(root_folder):
        for file_name in files:
            if file_name == '__manifest__.py':
                file_path = os.path.join(folder_name, file_name)

                # Read the content of the file
                with open(file_path, 'r') as file:
                    content = file.read()

                # Update the version string
                updated_content = re.sub(r"'version': '(\d+)\.", r"'version': '17.", content, count=1)


                # Write the updated content back to the file
                with open(file_path, 'w') as file:
                    file.write(updated_content)

                print(f"Updated version in {file_path}")


# Replace 'your_folder_path' with the actual path to your folder containing the modules
update_version('/home/shurikas/Documents/ODOO/odoo-17.0/repositories/crnd-inc/bureaucrat-knowledge')
