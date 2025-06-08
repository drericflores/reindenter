import tkinter as tk
from tkinter import filedialog, messagebox
import re

class PythonReindenterApp:
    """
    GUI application for reindenting Python source files using Tkinter.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Python Reindenter")

        # State variables
        self.filename = None
        self.indentation_applied = False
        self.version = "1.2"

        # Layout
        self.create_menu()
        self.text_display = tk.Text(self.root, wrap="none", state="disabled", font=("Courier", 12))
        self.text_display.pack(expand=True, fill="both")

        self.status_label = tk.Label(self.root, text="Welcome to Python Reindenter", anchor="w")
        self.status_label.pack(fill="x")

    def create_menu(self):
        menubar = tk.Menu(self.root)

        # File
        self.file_menu = tk.Menu(menubar, tearoff=0)
        self.file_menu.add_command(label="Load", command=self.load_file)
        self.file_menu.add_command(label="Save", command=self.save_file, state="disabled")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Quit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=self.file_menu)

        # Edit
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Reset Indentation", command=self.reset_indentation)
        edit_menu.add_command(label="Apply Indent", command=self.apply_indent)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        # Help
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.root.config(menu=menubar)

    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Python Files", "*.py")])
        if file_path:
            self.filename = file_path
            with open(self.filename, 'r') as file:
                code = file.read()
            self.display_code(code)
            self.indentation_applied = False
            self.update_save_state()
            self.set_status(f"Loaded: {self.filename}")

    def save_file(self):
        if self.filename and self.indentation_applied:
            with open(self.filename, 'w') as file:
                file.write(self.text_display.get("1.0", tk.END).strip())
            messagebox.showinfo("Save", f"File saved as {self.filename}")
            self.set_status(f"Saved: {self.filename}")

    def display_code(self, code):
        self.text_display.config(state="normal")
        self.text_display.delete("1.0", tk.END)
        self.text_display.insert("1.0", code)
        self.text_display.config(state="disabled")

    def reset_indentation(self):
        self.text_display.config(state="normal")
        code = self.text_display.get("1.0", tk.END).strip()
        self.text_display.config(state="disabled")

        stripped_code = "\n".join(line.replace('\t', ' ' * 4).lstrip() for line in code.splitlines())
        self.display_code(stripped_code)
        self.indentation_applied = False
        self.update_save_state()
        self.set_status("Indentation reset")

    def apply_indent(self, spaces=4):
        self.text_display.config(state="normal")
        code = self.text_display.get("1.0", tk.END).strip()
        self.text_display.config(state="disabled")

        lines = code.splitlines()
        indented_lines = []
        indent_level = 0
        inside_multiline_construct = False

        for line in lines:
            stripped = line.strip()

            if not stripped:
                indented_lines.append("")
                continue

            # Single-line docstring
            if stripped.startswith(('"""', "'''")):
                if stripped.endswith(('"""', "'''")) and len(stripped) > 6:
                    indented_lines.append(' ' * (indent_level * spaces) + stripped)
                    continue
                else:
                    inside_multiline_construct = not inside_multiline_construct
                    indented_lines.append(' ' * (indent_level * spaces) + stripped)
                    continue

            if inside_multiline_construct:
                indented_lines.append(' ' * (indent_level * spaces) + stripped)
                continue

            # Dedent for block keywords
            if re.match(r"^(elif|else|except|finally)\b", stripped):
                if indent_level > 0:
                    indent_level -= 1
                indented_lines.append(' ' * (indent_level * spaces) + stripped)
                indent_level += 1
                continue

            # Reset indent level if a new block (e.g., def/class)
            if re.match(r"^(def|class)\b", stripped):
                indent_level = 0

            indented_lines.append(' ' * (indent_level * spaces) + stripped)

            if stripped.endswith(":") and re.match(r"^(def|class|if|for|while|try|with|else|elif|except|finally)\b", stripped):
                indent_level += 1

        formatted_code = "\n".join(indented_lines)
        self.display_code(formatted_code)
        self.indentation_applied = True
        self.update_save_state()
        self.set_status("Indentation applied")

    def update_save_state(self):
        state = "normal" if self.indentation_applied else "disabled"
        self.file_menu.entryconfig("Save", state=state)

    def show_about(self):
        about_text = (
            "Python Indentation\n\n"
            "Program by Dr. Eric O. Flores\n"
            "Month: OCT 2024\n"
            f"Version: {self.version}\n"
            "ChatGPT enhanced code\n"
            "Copyright GPL3"
        )
        messagebox.showinfo("About", about_text)

    def set_status(self, msg):
        self.status_label.config(text=msg)


# Initialize
if __name__ == "__main__":
    root = tk.Tk()
    app = PythonReindenterApp(root)
    root.mainloop()
