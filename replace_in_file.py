import os
import re
import fileinput

def find_and_replace_in_file(file_to_find_in, text_to_find, text_to_replace, backup='', folder_path=False):
    """
    Recursively finds and replaces all occurrences of a string in a specified
    file within a given folder and its subdirectories.

    Args:
        file_to_find_in (str): The name of the file to search for.
        text_to_find (str): The string or regular expression pattern to search for.
        text_to_replace (str): The string to replace with.
        backup (str, optional): The suffix for creating backup files.
                                By default, backup is not provided.
        folder_path (str, optional): The path of the folder to search
                                     for the file (default is False).
                                     If not provided,
                                     the folder containing the script is used.

    Returns:
        None
    """

    if not folder_path:
        folder_path = os.path.dirname(os.path.abspath(__file__))
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            if filename.lower() == file_to_find_in:
                file_path = os.path.join(dirpath, filename)
                with fileinput.FileInput(file_path, inplace=True, backup=backup) as current_file:
                    for line in current_file:
                        print(re.sub(text_to_find, text_to_replace, line), end='')

# Example usage:
if __name__ == "__main__":
    # Replace versions '16.' with '17.' in all files recursively
    find_and_replace_in_file("__manifest__.py", r'\b16\.', '17.',
                             folder_path="/home/oleks/Documents/ODOO/odoo-16.0/repositories/crnd/bureaucrat-generics")
    # Set installable False
    find_and_replace_in_file("__manifest__.py", r"'installable'\s*:\s*True", "'installable': False", folder_path="/home/oleks/Documents/ODOO/odoo-16.0/repositories/crnd/bureaucrat-generics")
