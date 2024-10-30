import tkinter as tk
from tkinter import filedialog, messagebox
import re

class PythonReindenterApp:
    """
    Main GUI application for Python code indentation. Provides functionality to load, 
    reset, and apply standardized Python indentation with a Tkinter-based interface.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Python Reindenter")

        # Variables
        self.filename = None
        self.indentation_applied = False
        self.version = "1.2"

        # Setup Menu
        self.create_menu()

        # Code display area
        self.text_display = tk.Text(self.root, wrap="none", state="disabled", font=("Courier", 12))
        self.text_display.pack(expand=True, fill="both")

    def create_menu(self):
        """
        Initializes the menu for loading, saving, resetting indentation, and viewing About information.
        """
        menubar = tk.Menu(self.root)
        
        # File menu
        self.file_menu = tk.Menu(menubar, tearoff=0)
        self.file_menu.add_command(label="Load", command=self.load_file)
        self.file_menu.add_command(label="Save", command=self.save_file, state="disabled")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Quit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=self.file_menu)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Reset Indentation", command=self.reset_indentation)
        edit_menu.add_command(label="Apply Indent", command=self.apply_indent)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def load_file(self):
        """
        Opens a file dialog to select a Python file, then displays its contents in the text area.
        """
        file_path = filedialog.askopenfilename(filetypes=[("Python Files", "*.py")])
        if file_path:
            self.filename = file_path
            with open(self.filename, 'r') as file:
                code = file.read()
            self.display_code(code)
            self.indentation_applied = False  # Reset indentation state
            self.update_save_state()

    def save_file(self):
        """
        Saves the indented code back to the original file, enabled only after Apply Indent is used.
        """
        if self.filename and self.indentation_applied:
            with open(self.filename, 'w') as file:
                file.write(self.text_display.get("1.0", tk.END).strip())
            messagebox.showinfo("Save", f"File saved as {self.filename}")

    def display_code(self, code):
        """
        Displays code in the text area, making it read-only.
        """
        self.text_display.config(state="normal")
        self.text_display.delete("1.0", tk.END)
        self.text_display.insert("1.0", code)
        self.text_display.config(state="disabled")

    def reset_indentation(self):
        """
        Resets all indentation, removing any existing indents in the displayed code.
        """
        code = self.text_display.get("1.0", tk.END).strip()
        stripped_code = "\n".join(line.replace('\t', ' ' * 4).lstrip() for line in code.splitlines())
        self.display_code(stripped_code)
        self.indentation_applied = False
        self.update_save_state()

    def apply_indent(self, spaces=4):
        """
        Applies consistent indentation to the Python code, handling blocks and nested structures accurately.
        """
        code = self.text_display.get("1.0", tk.END).strip()
        lines = code.splitlines()
        indented_lines = []
        indent_level = 0
        inside_multiline_construct = False

        for line in lines:
            stripped_line = line.strip()

            # Skip applying indentation to empty lines
            if not stripped_line:
                indented_lines.append("")  # Keep the empty line as is
                continue

            # Handle multiline constructs (e.g., docstrings) without increasing indent level
            if stripped_line.startswith(('"""', "'''")) and not inside_multiline_construct:
                inside_multiline_construct = True
                indented_lines.append(' ' * (indent_level * spaces) + stripped_line)
                continue
            elif stripped_line.endswith(('"""', "'''")) and inside_multiline_construct:
                inside_multiline_construct = False
                indented_lines.append(' ' * (indent_level * spaces) + stripped_line)
                continue

            if inside_multiline_construct:
                indented_lines.append(' ' * (indent_level * spaces) + stripped_line)
                continue

            # Dedent for block closers that also act as new block openers (e.g., "elif", "else", "except", "finally")
            if stripped_line.startswith(("elif", "else", "except", "finally")):
                if indent_level > 0:
                    indent_level -= 1
                indented_lines.append(' ' * (indent_level * spaces) + stripped_line)
                indent_level += 1  # Re-indent for the new block
                continue

            # Reset indentation level for new definitions (e.g., def or class)
            if re.match(r"^(def |class )", stripped_line):
                indent_level = 0

            # Apply indentation for the current line
            indented_lines.append(' ' * (indent_level * spaces) + stripped_line)

            # Check if the current line is a block opener
            if stripped_line.endswith(":") and re.match(r'^(def |class |if |for |while |try:|except|finally)', stripped_line):
                indent_level += 1

        formatted_code = "\n".join(indented_lines)
        self.display_code(formatted_code)
        self.indentation_applied = True
        self.update_save_state()

    def update_save_state(self):
        """
        Enables or disables the Save option based on whether indentation has been applied.
        """
        self.file_menu.entryconfig("Save", state="normal" if self.indentation_applied else "disabled")

    def show_about(self):
        """
        Displays the About dialog with program information.
        """
        about_text = (
            "Python Indentation\n\n"
            "Program by Dr. Eric O. Flores\n"
            "Month: OCT 2024\n"
            f"Version: {self.version}\n"
            "ChatGPT enhanced code\n"
            "Copyright GPL3"
        )
        messagebox.showinfo("About", about_text)

# Initialize the application
root = tk.Tk()
app = PythonReindenterApp(root)
root.mainloop()

