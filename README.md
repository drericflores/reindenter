# reindenter
Python Code Reindenter for PEP8 Compliance (with GUI)
Description

This tool provides a graphical interface for the reindenter.py script, which reindents Python code to comply with PEP8 standards. It’s designed to help users clean up and standardize the indentation in Python scripts, making code more readable and organized. This GUI-based tool allows you to load a Python file, reset indentation, apply PEP8-compliant indentation, and save the updated file.

Features

File Upload: Select a .py file directly from your system to load it into the tool.
Reset Indentation: Remove existing indentation inconsistencies, replace tabs with spaces, and apply a uniform format.
Apply PEP8 Indentation: Re-indent the code following PEP8 standards, handling block structures and multi-line constructs.
Save File: Save the reformatted code back to your system.
How It Works

The GUI implementation includes the following main functions, accessible through buttons and options within the interface:

Load File: Loads the content of a Python file for reformatting.
Reset Indentation: Strips existing indentation inconsistencies and prepares the code for reindentation.
Apply Indent: Applies consistent indentation (default: 4 spaces) to the loaded code, following PEP8 recommendations.
Save File: Saves the reformatted code to a specified file location.
Usage

Open the GUI Application: Start the reindenter.py tool with the GUI option.
Load a Python File: Use the "Load File" button to select a .py file from your local directory.
View Original Code: Once loaded, the original code will display within the application window.
Reset and Reindent:
Reset Indentation: Click this option to remove any inconsistent or non-PEP8 indentation.
Apply PEP8 Indentation: Choose this to apply consistent, PEP8-compliant indentation (4 spaces per indent level).
Save the Formatted Code: Click the "Save File" button to save the reindented file to your preferred location.
Example Output

After following these steps, the reindented file will display consistent and clean indentation, improving readability and maintainability. You can also adjust the indentation level by specifying the number of spaces in the settings.

License

The reindenter.py script is released under the MIT License, which allows for free use, modification, and distribution.
